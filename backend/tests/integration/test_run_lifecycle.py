"""Integration tests for generation run queue and lifecycle."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.infrastructure.db.models import GenerationRun
from app.infrastructure.db.repositories.generation_run_repository import GenerationRunRepository
from app.workflows.run_lifecycle import prepare_run_for_execution

from tests.integration.helpers import create_org


@pytest.mark.asyncio
async def test_count_queue_ahead_includes_running_and_earlier_queued(
    db_session,
) -> None:
    org = await create_org(db_session)
    repo = GenerationRunRepository(db_session)
    now = datetime.now(UTC)

    running = GenerationRun(
        id=uuid.uuid4(),
        organization_id=org.id,
        module="listening",
        request={"module": "listening", "spec": {}},
        status="running",
        idempotency_key="run-a",
        started_at=now,
    )
    first_queued = GenerationRun(
        id=uuid.uuid4(),
        organization_id=org.id,
        module="listening",
        request={"module": "listening", "spec": {}},
        status="queued",
        idempotency_key="run-b",
        created_at=now,
    )
    second_queued = GenerationRun(
        id=uuid.uuid4(),
        organization_id=org.id,
        module="writing",
        request={"module": "writing", "spec": {}},
        status="queued",
        idempotency_key="run-c",
        created_at=now,
    )
    db_session.add_all([running, first_queued, second_queued])
    await db_session.flush()

    ahead = await repo.count_queue_ahead(second_queued, organization_id=org.id)
    assert ahead == 2


@pytest.mark.asyncio
async def test_prepare_run_for_execution_skips_failed_runs(db_session) -> None:
    org = await create_org(db_session)
    repo = GenerationRunRepository(db_session)
    run = GenerationRun(
        id=uuid.uuid4(),
        organization_id=org.id,
        module="smoke",
        request={"module": "smoke", "spec": {}},
        status="failed",
        failure_reason="Cancelled by operator",
        idempotency_key="run-failed",
    )
    db_session.add(run)
    await db_session.flush()

    assert await prepare_run_for_execution(repo, run) is False
    assert run.status == "failed"


@pytest.mark.asyncio
async def test_prepare_run_for_execution_sees_cancel_in_other_session(database_url) -> None:
    """Worker session must not resurrect a run cancelled while queued."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as worker_session:
        org = await create_org(worker_session)
        run = GenerationRun(
            id=uuid.uuid4(),
            organization_id=org.id,
            module="listening",
            request={"module": "listening", "spec": {}},
            status="queued",
            idempotency_key="run-cancel-race",
        )
        worker_session.add(run)
        await worker_session.commit()

        async with factory() as api_session:
            api_repo = GenerationRunRepository(api_session)
            cancelled = await api_repo.get_by_id(run.id)
            assert cancelled is not None
            await api_repo.mark_failed(cancelled, "Cancelled by operator")
            await api_session.commit()

        worker_repo = GenerationRunRepository(worker_session)
        assert await prepare_run_for_execution(worker_repo, run) is False
        assert run.status == "failed"

    await engine.dispose()
