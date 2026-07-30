"""Smoke graph unit tests."""

from __future__ import annotations

import pytest
from app.config import Settings
from app.infrastructure.db.models import AgentInvocation
from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.lease import InMemoryModelLease
from app.infrastructure.llm.types import ChatMessage, CompletionParams, ProviderResponse
from app.workflows.context import SmokeGraphContext
from app.workflows.graphs.smoke_graph import build_smoke_graph
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.helpers import create_org, create_run, create_user


class MetadataSchema(BaseModel):
    greeting: str


class MockProvider:
    name = "mock"

    async def complete(
        self,
        *,
        model: str,
        messages: tuple[ChatMessage, ...],
        params: CompletionParams,
        schema: type[BaseModel] | None = None,
    ) -> ProviderResponse:
        del model, messages, params, schema
        return ProviderResponse(
            content='{"greeting":"hello from smoke graph"}',
            input_tokens=5,
            output_tokens=3,
            latency_ms=50,
        )


@pytest.mark.asyncio
async def test_smoke_graph_completes_with_checkpoint(db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    user = await create_user(db_session, org)
    run = await create_run(db_session, org, user)
    await db_session.commit()

    gateway = LLMGateway(
        settings=Settings(llm_profile="fast"),
        lease=InMemoryModelLease(),
        provider=MockProvider(),
        session=db_session,
    )
    graph = build_smoke_graph(InMemorySaver())
    context = SmokeGraphContext(gateway=gateway, session=db_session)
    config = {"configurable": {"thread_id": str(run.id)}}

    final_state = await graph.ainvoke(
        {"run_id": str(run.id), "organization_id": str(org.id), "status": "queued"},
        config=config,
        context=context,
        durability="sync",
    )

    assert final_state["status"] == "completed"
    assert final_state["greeting"] == "hello from smoke graph"
    assert final_state["invocation_recorded"] is True

    count = await db_session.scalar(
        select(func.count()).select_from(AgentInvocation).where(AgentInvocation.run_id == run.id)
    )
    assert count == 1

    history = [state async for state in graph.aget_state_history(config)]
    assert len(history) >= 1
