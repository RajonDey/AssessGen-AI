"""Execute the Phase 1A smoke graph for a generation run."""

from __future__ import annotations

import importlib
import uuid

import redis.asyncio as aioredis
from sqlalchemy import func, select

from app.config import get_settings
from app.infrastructure.db.models import AgentInvocation
from app.infrastructure.db.repositories.generation_run_repository import GenerationRunRepository
from app.infrastructure.db.session import async_session_factory
from app.infrastructure.llm.gateway import ProviderError
from app.infrastructure.llm.structured import SchemaValidationError
from app.infrastructure.observability.logging import bind_run_context, get_logger
from app.workflows.checkpointer import postgres_checkpointer
from app.workflows.context import SmokeGraphContext
from app.workflows.graphs.smoke_graph import build_smoke_graph
from app.workflows.state import SmokeGraphState


class RunExecutionError(Exception):
    """Graph finished without a successful terminal state."""


async def execute_smoke_run(run_id: uuid.UUID) -> None:
    settings = get_settings()
    redis = aioredis.from_url(str(settings.redis_url))
    bind_run_context(str(run_id))
    log = get_logger("app.generation.runner")
    log.info("run.started")
    try:
        async with async_session_factory() as session:
            repo = GenerationRunRepository(session)
            run = await repo.get_by_id(run_id)
            if run is None:
                msg = f"Generation run {run_id} not found"
                raise RunExecutionError(msg)

            await repo.mark_running(run)
            await session.commit()

            final_state: SmokeGraphState
            try:
                async with postgres_checkpointer(settings) as checkpointer:
                    graph = build_smoke_graph(checkpointer)
                    factory = importlib.import_module("app.infrastructure.llm.factory")
                    gateway = factory.build_llm_gateway(
                        settings=settings,
                        session=session,
                        redis=redis,
                    )
                    context = SmokeGraphContext(gateway=gateway, session=session)
                    config = {"configurable": {"thread_id": str(run_id)}}
                    initial_state: SmokeGraphState = {
                        "run_id": str(run_id),
                        "organization_id": str(run.organization_id),
                        "status": "queued",
                    }
                    final_state = await graph.ainvoke(
                        initial_state,
                        config=config,
                        context=context,
                        durability="sync",
                    )
            except (SchemaValidationError, ProviderError) as exc:
                async with async_session_factory() as fail_session:
                    fail_repo = GenerationRunRepository(fail_session)
                    failed_run = await fail_repo.get_by_id(run_id)
                    if failed_run is not None:
                        await fail_repo.mark_failed(failed_run, str(exc))
                        await fail_session.commit()
                log.warning("run.failed", reason=str(exc))
                return

            run = await repo.get_by_id(run_id)
            if run is None:
                raise RunExecutionError(f"Generation run {run_id} disappeared during execution")

            if final_state.get("status") != "completed":
                reason = final_state.get("error") or "Smoke graph did not complete successfully"
                await repo.mark_failed(run, reason)
                await session.commit()
                log.warning("run.failed", reason=reason)
                return

            invocation_count = await session.scalar(
                select(func.count())
                .select_from(AgentInvocation)
                .where(AgentInvocation.run_id == run_id)
            )
            if not invocation_count:
                reason = "No agent invocations recorded for run"
                await repo.mark_failed(run, reason)
                await session.commit()
                log.warning("run.failed", reason=reason)
                return

            await repo.mark_completed(run)
            await session.commit()
            log.info("run.completed")
    except RunExecutionError:
        log.exception("run.failed")
        raise
    finally:
        await redis.aclose()
