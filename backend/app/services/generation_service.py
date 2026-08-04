"""Generation run application service."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import GenerationRun
from app.infrastructure.db.repositories.generation_run_repository import GenerationRunRepository
from app.infrastructure.queue.celery_app import celery_app
from app.infrastructure.queue.constants import GENERATE_QUEUE
from app.schemas.generation import CreateGenerationRunRequest, GenerationRunResponse
from app.services.generation_errors import RunCancelError

RUN_GENERATION_TASK = "app.workflows.generation_tasks.run_generation"
CANCELLED_REASON = "Cancelled by operator"


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

    async def get_run(
        self,
        run_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
    ) -> GenerationRun | None:
        return await self.runs.get_by_id(run_id, organization_id=organization_id)

    async def cancel_run(
        self,
        run_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
    ) -> GenerationRun:
        run = await self.runs.get_by_id(run_id, organization_id=organization_id)
        if run is None:
            msg = f"Generation run {run_id} not found"
            raise RunCancelError(msg)
        if run.status not in {"queued", "running"}:
            msg = f"Run cannot be cancelled while status is {run.status}"
            raise RunCancelError(msg)
        await self.runs.mark_failed(run, CANCELLED_REASON)
        await self.session.commit()
        return run

    async def to_response(
        self,
        run: GenerationRun,
        *,
        organization_id: uuid.UUID | None = None,
    ) -> GenerationRunResponse:
        queue_ahead: int | None = None
        if run.status == "queued" and organization_id is not None:
            queue_ahead = await self.runs.count_queue_ahead(run, organization_id=organization_id)
        return GenerationRunResponse(
            run_id=run.id,
            status=run.status,
            module=run.module,
            created_at=run.created_at,
            failure_reason=run.failure_reason,
            queue_ahead=queue_ahead,
            started_at=run.started_at,
        )

    @staticmethod
    def to_response_sync(run: GenerationRun) -> GenerationRunResponse:
        return GenerationRunResponse(
            run_id=run.id,
            status=run.status,
            module=run.module,
            created_at=run.created_at,
            failure_reason=run.failure_reason,
            started_at=run.started_at,
        )
