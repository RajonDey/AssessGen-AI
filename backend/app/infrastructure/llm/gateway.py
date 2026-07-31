"""LLM gateway — role routing, leasing, structured output, accounting."""

from __future__ import annotations

import uuid
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.infrastructure.llm.accounting import record_invocation
from app.infrastructure.llm.lease import ModelLease
from app.infrastructure.llm.profiles import resolve_model
from app.infrastructure.llm.providers.base import LLMProvider
from app.infrastructure.llm.structured import SchemaValidationError, complete_with_repair
from app.infrastructure.llm.types import (
    ChatMessage,
    CompletionParams,
    GatewayRequest,
    LLMRole,
    hash_messages,
)
from app.infrastructure.observability.logging import bind_run_context, get_logger

T = TypeVar("T", bound=BaseModel)


class ProviderError(Exception):
    """Provider call failed before a usable response was returned."""


class LLMGateway:
    def __init__(
        self,
        *,
        settings: Settings,
        lease: ModelLease,
        provider: LLMProvider,
        session: AsyncSession,
    ) -> None:
        self.settings = settings
        self.lease = lease
        self.provider = provider
        self.session = session

    async def complete(
        self,
        *,
        role: LLMRole | str,
        agent: str,
        run_id: uuid.UUID,
        messages: tuple[ChatMessage, ...] | list[ChatMessage],
        schema: type[T],
        prompt_hash: str | None = None,
        prompt_version_id: uuid.UUID | None = None,
        params: CompletionParams | None = None,
    ) -> T:
        msg_tuple = tuple(messages)
        request = GatewayRequest(
            role=LLMRole(role),
            agent=agent,
            run_id=run_id,
            messages=msg_tuple,
            prompt_hash=prompt_hash or hash_messages(msg_tuple),
            prompt_version_id=prompt_version_id,
            params=params or CompletionParams(),
        )
        model = resolve_model(self.settings.llm_profile, request.role)
        bind_run_context(str(request.run_id))
        log = get_logger("app.llm.gateway")

        async with self.lease.hold(model.model_name, model.memory_gb):
            log.info(
                "agent.invocation.started",
                agent=request.agent,
                role=str(request.role),
                model=model.model_name,
            )
            try:
                structured = await complete_with_repair(
                    schema=schema,
                    base_messages=request.messages,
                    invoke=lambda msgs: self.provider.complete(
                        model=model.model_name,
                        messages=msgs,
                        params=request.params,
                        schema=schema,
                    ),
                )
            except SchemaValidationError as exc:
                for attempt in exc.attempts:
                    await record_invocation(
                        self.session,
                        run_id=request.run_id,
                        agent=request.agent,
                        role=request.role,
                        provider=model.provider,
                        model_name=model.model_name,
                        prompt_hash=request.prompt_hash,
                        params=request.params,
                        response=attempt.response,
                        status="schema_error",
                        attempt=attempt.attempt,
                        prompt_version_id=request.prompt_version_id,
                        error_detail=attempt.validation_error,
                    )
                await self.session.commit()
                log.warning(
                    "agent.invocation.schema_error",
                    agent=request.agent,
                    role=str(request.role),
                    model=model.model_name,
                    attempts=len(exc.attempts),
                )
                raise
            except Exception as exc:
                await record_invocation(
                    self.session,
                    run_id=request.run_id,
                    agent=request.agent,
                    role=request.role,
                    provider=model.provider,
                    model_name=model.model_name,
                    prompt_hash=request.prompt_hash,
                    params=request.params,
                    response=None,
                    status="provider_error",
                    attempt=1,
                    prompt_version_id=request.prompt_version_id,
                    error_detail=str(exc),
                )
                await self.session.commit()
                raise ProviderError(str(exc)) from exc

            for attempt in structured.attempts:
                await record_invocation(
                    self.session,
                    run_id=request.run_id,
                    agent=request.agent,
                    role=request.role,
                    provider=model.provider,
                    model_name=model.model_name,
                    prompt_hash=request.prompt_hash,
                    params=request.params,
                    response=attempt.response,
                    status="success" if attempt.parsed is not None else "schema_error",
                    attempt=attempt.attempt,
                    prompt_version_id=request.prompt_version_id,
                    error_detail=attempt.validation_error,
                )
            await self.session.commit()

            final_attempt = structured.attempts[-1]
            log.info(
                "agent.invocation.completed",
                agent=request.agent,
                role=str(request.role),
                model=model.model_name,
                input_tokens=final_attempt.response.input_tokens,
                output_tokens=final_attempt.response.output_tokens,
                latency_ms=final_attempt.response.latency_ms,
                attempt=final_attempt.attempt,
            )
            return structured.value  # type: ignore[return-value]

    async def embed(
        self,
        *,
        run_id: uuid.UUID,
        text: str,
        role: LLMRole | str = LLMRole.EMBEDDING,
    ) -> list[float]:
        request_role = LLMRole(role)
        model = resolve_model(self.settings.llm_profile, request_role)
        bind_run_context(str(run_id))
        log = get_logger("app.llm.gateway")

        async with self.lease.hold(model.model_name, model.memory_gb):
            log.info(
                "agent.embedding.started",
                role=str(request_role),
                model=model.model_name,
            )
            try:
                vector = await self.provider.embed(model=model.model_name, text=text)
            except Exception as exc:
                log.warning("agent.embedding.failed", reason=str(exc))
                raise ProviderError(str(exc)) from exc

            log.info(
                "agent.embedding.completed",
                role=str(request_role),
                model=model.model_name,
                dimensions=len(vector),
            )
            return vector
