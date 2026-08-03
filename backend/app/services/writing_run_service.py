"""Execute and resume the IELTS Writing graph for a generation run."""

from __future__ import annotations

import uuid
from typing import Any

import redis.asyncio as aioredis
from langgraph.types import Command
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain.enums import RunStatus
from app.infrastructure.db.models import AgentInvocation
from app.infrastructure.db.repositories.generation_run_repository import GenerationRunRepository
from app.infrastructure.db.session import async_session_factory
from app.infrastructure.llm.gateway import ProviderError
from app.infrastructure.llm.structured import SchemaValidationError
from app.infrastructure.observability.logging import bind_run_context, get_logger
from app.modules.ielts.writing.request import WritingGenerationSpec, parse_writing_spec
from app.services.reading_quality import build_reading_graph_context
from app.workflows.checkpointer import postgres_checkpointer
from app.workflows.graphs.writing_graph import build_writing_graph
from app.workflows.smoke_runner import RunExecutionError
from app.workflows.writing_runner import build_initial_writing_state
from app.workflows.writing_state import WritingGraphState


def _graph_is_interrupted(result: dict[str, Any]) -> bool:
    return bool(result.get("__interrupt__"))


async def _schema_failure_reason(
    session: AsyncSession,
    run_id: uuid.UUID,
    exc: SchemaValidationError,
) -> str:
    detail = exc.attempts[-1].validation_error if exc.attempts else str(exc)
    agent = await session.scalar(
        select(AgentInvocation.agent)
        .where(
            AgentInvocation.run_id == run_id,
            AgentInvocation.status == "schema_error",
        )
        .order_by(AgentInvocation.created_at.desc())
        .limit(1)
    )
    label = agent or "structured_output"
    return f"{label}: {(detail or str(exc))[:400]}"


async def _invoke_writing_graph(
    *,
    session: AsyncSession,
    run_id: uuid.UUID,
    organization_id: uuid.UUID,
    spec: WritingGenerationSpec,
    command: WritingGraphState | Command | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    redis = aioredis.from_url(str(settings.redis_url))  # type: ignore[no-untyped-call]
    try:
        async with postgres_checkpointer(settings) as checkpointer:
            graph = build_writing_graph(checkpointer)
            context = await build_reading_graph_context(
                settings=settings,
                session=session,
                redis=redis,
                organization_id=organization_id,
            )
            config = {"configurable": {"thread_id": str(run_id)}}
            if command is None:
                invoke_input: WritingGraphState | Command = build_initial_writing_state(
                    run_id=run_id,
                    organization_id=organization_id,
                    spec=spec,
                )
            else:
                invoke_input = command
            return await graph.ainvoke(
                invoke_input,
                config=config,
                context=context,
                durability="sync",
            )
    finally:
        await redis.aclose()


async def execute_writing_run(run_id: uuid.UUID) -> None:
    bind_run_context(str(run_id))
    log = get_logger("app.generation.writing_runner")
    log.info("run.started")
    try:
        async with async_session_factory() as session:
            repo = GenerationRunRepository(session)
            run = await repo.get_by_id(run_id)
            if run is None:
                msg = f"Generation run {run_id} not found"
                raise RunExecutionError(msg)

            try:
                spec = parse_writing_spec(run.request)
            except ValueError as exc:
                await repo.mark_failed(run, str(exc))
                await session.commit()
                log.warning("run.failed", reason=str(exc))
                return

            await repo.mark_running(run)
            await session.commit()

            try:
                final_state = await _invoke_writing_graph(
                    session=session,
                    run_id=run_id,
                    organization_id=run.organization_id,
                    spec=spec,
                )
            except (SchemaValidationError, ProviderError) as exc:
                reason = (
                    await _schema_failure_reason(session, run_id, exc)
                    if isinstance(exc, SchemaValidationError)
                    else str(exc)
                )
                await repo.mark_failed(run, reason)
                await session.commit()
                log.warning("run.failed", reason=str(exc))
                return

            run = await repo.get_by_id(run_id)
            if run is None:
                raise RunExecutionError(f"Generation run {run_id} disappeared during execution")

            if _graph_is_interrupted(final_state):
                await repo.mark_awaiting_review(run)
                await session.commit()
                log.info("run.awaiting_review")
                return

            if final_state.get("status") != "completed":
                reason = final_state.get("error") or "Writing graph did not complete successfully"
                await repo.mark_failed(run, str(reason))
                await session.commit()
                log.warning("run.failed", reason=reason)
                return

            invocation_count = await session.scalar(
                select(func.count())
                .select_from(AgentInvocation)
                .where(AgentInvocation.run_id == run_id)
            )
            if not invocation_count:
                reason = "No agent invocations recorded for writing run"
                await repo.mark_failed(run, reason)
                await session.commit()
                log.warning("run.failed", reason=reason)
                return

            await repo.mark_completed(run)
            await session.commit()
            log.info("run.completed", question_type=spec.question_type)
    except RunExecutionError:
        log.exception("run.failed")
        raise


async def resume_writing_run(
    run_id: uuid.UUID,
    *,
    decision: dict[str, Any],
    organization_id: uuid.UUID,
) -> dict[str, Any]:
    bind_run_context(str(run_id))
    log = get_logger("app.generation.writing_runner")
    async with async_session_factory() as session:
        repo = GenerationRunRepository(session)
        run = await repo.get_by_id(run_id, organization_id=organization_id)
        if run is None:
            msg = f"Generation run {run_id} not found"
            raise RunExecutionError(msg)
        if run.status != RunStatus.AWAITING_REVIEW.value:
            msg = f"Run {run_id} is not awaiting review (status={run.status})"
            raise RunExecutionError(msg)

        await repo.mark_running(run)
        await session.commit()

        spec = parse_writing_spec(run.request)
        final_state = await _invoke_writing_graph(
            session=session,
            run_id=run_id,
            organization_id=run.organization_id,
            spec=spec,
            command=Command(resume=decision),
        )

        run = await repo.get_by_id(run_id)
        if run is None:
            raise RunExecutionError(f"Generation run {run_id} disappeared during resume")

        if _graph_is_interrupted(final_state):
            await repo.mark_awaiting_review(run)
            await session.commit()
            log.info("run.awaiting_review")
            return final_state

        if final_state.get("status") != "completed":
            reason = final_state.get("error") or "Writing graph did not complete after review"
            await repo.mark_failed(run, str(reason))
            await session.commit()
            raise RunExecutionError(reason)

        await repo.mark_completed(run)
        await session.commit()
        log.info("run.completed", resumed=True)
        return final_state
