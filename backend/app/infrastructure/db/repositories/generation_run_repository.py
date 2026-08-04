"""Generation run persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import GenerationRun


class GenerationRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self,
        run_id: uuid.UUID,
        *,
        organization_id: uuid.UUID | None = None,
    ) -> GenerationRun | None:
        stmt = select(GenerationRun).where(GenerationRun.id == run_id)
        if organization_id is not None:
            stmt = stmt.where(GenerationRun.organization_id == organization_id)
        return cast(GenerationRun | None, await self.session.scalar(stmt))

    async def get_by_idempotency_key(
        self,
        organization_id: uuid.UUID,
        idempotency_key: str,
    ) -> GenerationRun | None:
        stmt = select(GenerationRun).where(
            GenerationRun.organization_id == organization_id,
            GenerationRun.idempotency_key == idempotency_key,
        )
        return cast(GenerationRun | None, await self.session.scalar(stmt))

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        module: str,
        request: dict[str, Any],
        requested_by: uuid.UUID | None,
        idempotency_key: str,
        status: str = "queued",
    ) -> GenerationRun:
        run = GenerationRun(
            id=uuid.uuid4(),
            organization_id=organization_id,
            module=module,
            request=request,
            status=status,
            idempotency_key=idempotency_key,
            requested_by=requested_by,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def mark_running(self, run: GenerationRun) -> None:
        run.status = "running"
        run.started_at = datetime.now(UTC)

    async def mark_awaiting_review(self, run: GenerationRun) -> None:
        run.status = "awaiting_review"
        run.failure_reason = None

    async def mark_completed(self, run: GenerationRun) -> None:
        run.status = "completed"
        run.finished_at = datetime.now(UTC)
        run.failure_reason = None

    async def list_awaiting_review(
        self,
        organization_id: uuid.UUID,
        *,
        limit: int = 20,
    ) -> tuple[GenerationRun, ...]:
        stmt = (
            select(GenerationRun)
            .where(
                GenerationRun.organization_id == organization_id,
                GenerationRun.status == "awaiting_review",
            )
            .order_by(GenerationRun.created_at)
            .limit(limit)
        )
        rows = (await self.session.scalars(stmt)).all()
        return tuple(rows)

    async def mark_failed(self, run: GenerationRun, reason: str) -> None:
        run.status = "failed"
        run.failure_reason = reason
        run.finished_at = datetime.now(UTC)

    async def count_queue_ahead(
        self,
        run: GenerationRun,
        *,
        organization_id: uuid.UUID,
    ) -> int:
        """Runs ahead of this one: one slot if a worker is busy, plus earlier queued runs."""
        running_stmt = (
            select(func.count())
            .select_from(GenerationRun)
            .where(
                GenerationRun.organization_id == organization_id,
                GenerationRun.status == "running",
            )
        )
        running_count = int(await self.session.scalar(running_stmt) or 0)
        queued_stmt = (
            select(func.count())
            .select_from(GenerationRun)
            .where(
                GenerationRun.organization_id == organization_id,
                GenerationRun.status == "queued",
                GenerationRun.created_at < run.created_at,
            )
        )
        queued_ahead = int(await self.session.scalar(queued_stmt) or 0)
        return running_count + queued_ahead

