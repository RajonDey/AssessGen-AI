"""Gateway integration tests — persistence and role resolution."""

from __future__ import annotations

import pytest
from app.config import Settings
from app.infrastructure.db.models import AgentInvocation
from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.lease import InMemoryModelLease
from app.infrastructure.llm.types import ChatMessage, CompletionParams, LLMRole, ProviderResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.helpers import create_org, create_run, create_user


class MetadataSchema(BaseModel):
    greeting: str = Field(min_length=1)


class MockProvider:
    name = "mock"

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.calls = 0

    async def complete(
        self,
        *,
        model: str,
        messages: tuple[ChatMessage, ...],
        params: CompletionParams,
        schema: type[BaseModel] | None = None,
    ) -> ProviderResponse:
        del model, messages, params, schema
        content = self._responses[min(self.calls, len(self._responses) - 1)]
        self.calls += 1
        return ProviderResponse(
            content=content,
            input_tokens=12,
            output_tokens=8,
            latency_ms=250,
            model_digest=f"digest:{self.calls}",
        )


@pytest.mark.asyncio
async def test_gateway_persists_successful_invocation(db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    user = await create_user(db_session, org)
    run = await create_run(db_session, org, user)

    gateway = LLMGateway(
        settings=Settings(llm_profile="fast"),
        lease=InMemoryModelLease(),
        provider=MockProvider(['{"greeting":"hello"}']),
        session=db_session,
    )

    result = await gateway.complete(
        role=LLMRole.METADATA,
        agent="metadata_agent",
        run_id=run.id,
        messages=[ChatMessage(role="user", content="Return a greeting.")],
        schema=MetadataSchema,
        prompt_hash="abc123",
    )

    assert result.greeting == "hello"
    rows = (
        await db_session.scalars(select(AgentInvocation).where(AgentInvocation.run_id == run.id))
    ).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.role == "metadata"
    assert row.model_name == "qwen3.5:4b"
    assert row.prompt_hash == "abc123"
    assert row.input_tokens == 12
    assert row.output_tokens == 8
    assert row.status == "success"


@pytest.mark.asyncio
async def test_gateway_records_each_repair_attempt(db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    user = await create_user(db_session, org)
    run = await create_run(db_session, org, user)

    gateway = LLMGateway(
        settings=Settings(llm_profile="fast"),
        lease=InMemoryModelLease(),
        provider=MockProvider(['{"greeting":""}', '{"greeting":"hi"}']),
        session=db_session,
    )

    result = await gateway.complete(
        role="metadata",
        agent="metadata_agent",
        run_id=run.id,
        messages=(ChatMessage(role="user", content="Return a greeting."),),
        schema=MetadataSchema,
    )

    assert result.greeting == "hi"
    rows = (
        await db_session.scalars(
            select(AgentInvocation)
            .where(AgentInvocation.run_id == run.id)
            .order_by(AgentInvocation.attempt)
        )
    ).all()
    assert len(rows) == 2
    assert rows[0].attempt == 1
    assert rows[0].status == "schema_error"
    assert rows[1].attempt == 2
    assert rows[1].status == "success"
