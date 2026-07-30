"""Generation run application service."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import GenerationRun
from app.infrastructure.db.repositories.generation_run_repository import GenerationRunRepository
from app.infrastructure.queue.celery_app import celery_app
from app.infrastructure.queue.constants import GENERATE_QUEUE
from app.schemas.generation import CreateGenerationRunRequest, GenerationRunResponse

RUN_GENERATION_TASK = "app.workflows.generation_tasks.run_generation"


class DuplicateIdempotencyKeyError(Exception):
    def __init__(self, existing: GenerationRun) -> None:
        self.existing = existing
        super().__init__("Idempotency key conflict")


class GenerationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = GenerationRunRepository(session)

    async def create_smoke_run(
        self,
        *,
        organization_id: uuid.UUID,
        requested_by: uuid.UUID,
        idempotency_key: str,
        body: CreateGenerationRunRequest,
    ) -> GenerationRun:
        existing = await self.runs.get_by_idempotency_key(organization_id, idempotency_key)
        if existing is not None:
            if existing.request != body.model_dump():
                raise DuplicateIdempotencyKeyError(existing)
            return existing

        run = await self.runs.create(
            organization_id=organization_id,
            module=body.module,
            request=body.model_dump(),
            requested_by=requested_by,
            idempotency_key=idempotency_key,
        )
        await self.session.commit()
        celery_app.send_task(
            RUN_GENERATION_TASK,
            args=[str(run.id)],
            queue=GENERATE_QUEUE,
        )
        return run

    @staticmethod
    def to_response(run: GenerationRun) -> GenerationRunResponse:
        return GenerationRunResponse(
            run_id=run.id,
            status=run.status,
            module=run.module,
            created_at=run.created_at,
            failure_reason=run.failure_reason,
        )
