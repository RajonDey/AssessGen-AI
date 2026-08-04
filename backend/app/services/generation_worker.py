"""Dispatch generation runs to the appropriate module graph."""

from __future__ import annotations

import asyncio
import uuid

from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded

from app.config import get_settings
from app.domain.enums import RunStatus
from app.infrastructure.observability.logging import bind_run_context, clear_log_context, get_logger
from app.infrastructure.queue.base import AssessGenTask
from app.infrastructure.queue.celery_app import celery_app
from app.infrastructure.queue.constants import GENERATE_QUEUE
from app.infrastructure.queue.errors import ContentTaskError, InfrastructureTaskError
from app.services.listening_run_service import execute_listening_run
from app.services.reading_run_service import execute_reading_run
from app.services.speaking_run_service import execute_speaking_run
from app.services.writing_run_service import execute_writing_run
from app.workflows.smoke_runner import RunExecutionError, execute_smoke_run


from app.services.generation_service import CANCELLED_REASON

_settings = get_settings()


@celery_app.task(
    name="app.workflows.generation_tasks.run_generation",
    base=AssessGenTask,
    bind=True,
    queue=GENERATE_QUEUE,
    soft_time_limit=_settings.generation_soft_timeout_seconds,
    time_limit=_settings.generation_hard_timeout_seconds,
)
def run_generation(self: AssessGenTask, run_id: str) -> dict[str, str]:
    bind_run_context(run_id)
    log = get_logger("app.generation.worker")
    log.info("run.queued", celery_task_id=self.request.id)
    try:
        parsed_run_id = uuid.UUID(run_id)
    except ValueError as exc:
        raise ContentTaskError(f"Invalid run_id: {run_id}") from exc

    try:
        asyncio.run(_execute_run(parsed_run_id))
    except (SoftTimeLimitExceeded, TimeLimitExceeded) as exc:
        asyncio.run(_mark_run_timed_out(parsed_run_id))
        raise ContentTaskError("Generation run timed out") from exc
    except RunExecutionError as exc:
        raise ContentTaskError(str(exc)) from exc
    except Exception as exc:
        raise InfrastructureTaskError(str(exc)) from exc
    finally:
        clear_log_context()

    return {
        "run_id": run_id,
        "status": "completed",
        "task_id": self.request.id or "",
    }


async def _execute_run(run_id: uuid.UUID) -> None:
    from app.infrastructure.db.repositories.generation_run_repository import GenerationRunRepository
    from app.infrastructure.db.session import async_session_factory

    async with async_session_factory() as session:
        repo = GenerationRunRepository(session)
        run = await repo.get_by_id(run_id)
        if run is None:
            msg = f"Generation run {run_id} not found"
            raise RunExecutionError(msg)
        if run.status == RunStatus.FAILED.value:
            if run.failure_reason == CANCELLED_REASON:
                get_logger("app.generation.worker").info("run.skipped_cancelled")
            return
        if run.status in {RunStatus.COMPLETED.value, RunStatus.AWAITING_REVIEW.value}:
            return
        module = run.module

    if module == "smoke":
        await execute_smoke_run(run_id)
        return
    if module == "reading":
        await execute_reading_run(run_id)
        return
    if module == "listening":
        await execute_listening_run(run_id)
        return
    if module == "writing":
        await execute_writing_run(run_id)
        return
    if module == "speaking":
        await execute_speaking_run(run_id)
        return

    msg = f"Unsupported generation module: {module}"
    raise RunExecutionError(msg)


async def _mark_run_timed_out(run_id: uuid.UUID) -> None:
    from app.infrastructure.db.repositories.generation_run_repository import GenerationRunRepository
    from app.infrastructure.db.session import async_session_factory

    settings = get_settings()
    reason = (
        f"Generation exceeded {settings.generation_soft_timeout_seconds}s soft timeout "
        f"({settings.generation_hard_timeout_seconds}s hard limit)"
    )
    async with async_session_factory() as session:
        repo = GenerationRunRepository(session)
        run = await repo.get_by_id(run_id)
        if run is not None and run.status in {RunStatus.QUEUED.value, RunStatus.RUNNING.value}:
            await repo.mark_failed(run, reason)
            await session.commit()
