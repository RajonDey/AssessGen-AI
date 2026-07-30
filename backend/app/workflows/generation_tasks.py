"""Celery task for smoke graph execution."""

from __future__ import annotations

import asyncio
import uuid

from app.infrastructure.observability.logging import bind_run_context, clear_log_context, get_logger
from app.infrastructure.queue.base import AssessGenTask
from app.infrastructure.queue.celery_app import celery_app
from app.infrastructure.queue.constants import GENERATE_QUEUE
from app.infrastructure.queue.errors import ContentTaskError, InfrastructureTaskError
from app.workflows.smoke_runner import RunExecutionError, execute_smoke_run


@celery_app.task(
    name="app.workflows.generation_tasks.run_generation",
    base=AssessGenTask,
    bind=True,
    queue=GENERATE_QUEUE,
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
        asyncio.run(execute_smoke_run(parsed_run_id))
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
