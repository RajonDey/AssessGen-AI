"""End-to-end smoke run execution."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, cast

import pytest
from app.config import Settings
from app.infrastructure.db.models import AgentInvocation, GenerationRun
from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.lease import InMemoryModelLease
from app.infrastructure.llm.types import ChatMessage, CompletionParams, ProviderResponse
from app.workflows.checkpointer import reset_checkpoint_schema_flag
from app.workflows.smoke_runner import execute_smoke_run
from pydantic import BaseModel, PostgresDsn
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.helpers import create_org, create_run, create_user

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


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
            content='{"greeting":"hello"}',
            input_tokens=7,
            output_tokens=4,
            latency_ms=120,
        )

    async def embed(self, *, model: str, text: str) -> list[float]:
        del model, text
        return [0.0] * 768


class _TestSessionFactory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[AsyncSession]:
        yield self._session


@pytest.mark.asyncio
async def test_execute_smoke_run_persists_invocation_and_checkpoint(
    db_session: AsyncSession,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_checkpoint_schema_flag()
    org = await create_org(db_session)
    user = await create_user(db_session, org)
    run = await create_run(db_session, org, user)
    await db_session.commit()
    run_id = run.id

    monkeypatch.setattr(
        "app.workflows.smoke_runner.get_settings",
        lambda: Settings(
            database_url=cast(PostgresDsn, database_url),
            llm_profile="fast",
        ),
    )
    monkeypatch.setattr(
        "app.workflows.smoke_runner.async_session_factory",
        _TestSessionFactory(db_session),
    )
    monkeypatch.setattr(
        "app.infrastructure.llm.factory.build_llm_gateway",
        lambda **kwargs: LLMGateway(
            settings=Settings(llm_profile="fast"),
            lease=InMemoryModelLease(),
            provider=MockProvider(),
            session=kwargs["session"],
        ),
    )

    await execute_smoke_run(run_id)

    db_session.expire_all()
    refreshed = await db_session.get(GenerationRun, run_id)
    assert refreshed is not None
    assert refreshed.status == "completed"

    invocations = await db_session.scalar(
        select(func.count()).select_from(AgentInvocation).where(AgentInvocation.run_id == run_id)
    )
    assert invocations == 1

    result = await db_session.execute(
        text("SELECT count(*) FROM checkpoints WHERE thread_id = :thread_id"),
        {"thread_id": str(run_id)},
    )
    checkpoint_count = result.scalar_one()
    assert checkpoint_count >= 1
