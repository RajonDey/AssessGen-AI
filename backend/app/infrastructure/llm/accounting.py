"""Persist gateway call accounting to agent_invocations."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import AgentInvocation
from app.infrastructure.llm.types import CompletionParams, LLMRole, ProviderResponse


def _tokens_per_second(response: ProviderResponse) -> Decimal | None:
    if response.latency_ms <= 0 or response.output_tokens <= 0:
        return None
    return Decimal(response.output_tokens) / (Decimal(response.latency_ms) / Decimal(1000))


async def record_invocation(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    agent: str,
    role: LLMRole | str,
    provider: str,
    model_name: str,
    prompt_hash: str,
    params: CompletionParams,
    response: ProviderResponse | None,
    status: str,
    attempt: int,
    prompt_version_id: uuid.UUID | None = None,
    error_detail: str | None = None,
) -> AgentInvocation:
    input_tokens = response.input_tokens if response else None
    output_tokens = response.output_tokens if response else None
    latency_ms = response.latency_ms if response else None
    tokens_per_second = _tokens_per_second(response) if response else None

    row = AgentInvocation(
        id=uuid.uuid4(),
        run_id=run_id,
        agent=agent,
        role=str(role),
        provider=provider,
        model_name=model_name,
        model_digest=response.model_digest if response else None,
        prompt_version_id=prompt_version_id,
        prompt_hash=prompt_hash,
        params=params.as_dict(),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        tokens_per_second=tokens_per_second,
        cost_usd=Decimal("0"),
        status=status,
        error_detail=error_detail,
        attempt=attempt,
    )
    session.add(row)
    await session.flush()
    return row
