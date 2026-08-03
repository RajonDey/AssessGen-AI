"""Human review queue and decisions."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.generation_run_repository import GenerationRunRepository
from app.schemas.review import ReviewQueueItem, ReviewQueueResponse
from app.services.listening_run_service import RunExecutionError, resume_listening_run
from app.services.reading_run_service import resume_reading_run
from app.services.speaking_run_service import resume_speaking_run
from app.services.writing_run_service import resume_writing_run


class ReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = GenerationRunRepository(session)

    async def list_queue(self, organization_id: uuid.UUID) -> ReviewQueueResponse:
        rows = await self.runs.list_awaiting_review(organization_id)
        items: list[ReviewQueueItem] = []
        for run in rows:
            topic = None
            spec = run.request.get("spec") if isinstance(run.request, dict) else None
            if isinstance(spec, dict):
                topic = spec.get("topic")
            items.append(
                ReviewQueueItem(
                    run_id=run.id,
                    module=run.module,
                    topic=topic,
                    created_at=run.created_at,
                )
            )
        return ReviewQueueResponse(items=items)

    async def resume_run(
        self,
        *,
        run_id: uuid.UUID,
        organization_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        decision = {
            **body,
            "reviewer_id": str(reviewer_id),
        }
        try:
            run = await self.runs.get_by_id(run_id, organization_id=organization_id)
            if run is None:
                msg = f"Generation run {run_id} not found"
                raise RunExecutionError(msg)
            if run.module == "listening":
                return await resume_listening_run(
                    run_id,
                    decision=decision,
                    organization_id=organization_id,
                )
            if run.module == "writing":
                return await resume_writing_run(
                    run_id,
                    decision=decision,
                    organization_id=organization_id,
                )
            if run.module == "speaking":
                return await resume_speaking_run(
                    run_id,
                    decision=decision,
                    organization_id=organization_id,
                )
            return await resume_reading_run(
                run_id,
                decision=decision,
                organization_id=organization_id,
            )
        except RunExecutionError as exc:
            raise ReviewResumeError(str(exc)) from exc


class ReviewResumeError(Exception):
    """Review resume could not complete."""
