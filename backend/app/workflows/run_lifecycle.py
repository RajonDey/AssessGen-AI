"""Shared generation run lifecycle helpers for workflow execution."""

from __future__ import annotations

from app.domain.enums import RunStatus
from app.infrastructure.db.models import GenerationRun
from app.infrastructure.db.repositories.generation_run_repository import GenerationRunRepository


async def prepare_run_for_execution(
    repo: GenerationRunRepository,
    run: GenerationRun,
) -> bool:
    """Mark a queued run as running. Returns False if the worker should skip execution."""
    await repo.session.refresh(run)
    if run.status == RunStatus.FAILED.value:
        return False
    if run.status in {RunStatus.COMPLETED.value, RunStatus.AWAITING_REVIEW.value}:
        return False
    if run.status == RunStatus.QUEUED.value:
        await repo.mark_running(run)
    return True
