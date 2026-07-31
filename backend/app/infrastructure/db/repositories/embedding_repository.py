"""Embedding persistence and similarity search."""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import select

from app.infrastructure.db.models.embedding import EMBEDDING_DIMENSIONS, Embedding
from app.infrastructure.db.repositories.base import TenantScopedRepository


class EmbeddingRepository(TenantScopedRepository):
    async def find_similar(
        self,
        *,
        vector: list[float],
        kind: str,
        model_name: str,
        limit: int = 5,
    ) -> list[tuple[uuid.UUID, str, float]]:
        if len(vector) != EMBEDDING_DIMENSIONS:
            msg = f"Expected {EMBEDDING_DIMENSIONS}-d vector, got {len(vector)}"
            raise ValueError(msg)

        distance = Embedding.embedding.cosine_distance(vector)
        stmt = (
            select(Embedding.target_id, Embedding.target_type, distance.label("distance"))
            .where(
                Embedding.kind == kind,
                Embedding.model_name == model_name,
            )
            .order_by(distance)
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        hits: list[tuple[uuid.UUID, str, float]] = []
        for target_id, target_type, raw_distance in rows:
            distance_value = float(cast(Any, raw_distance))
            similarity = max(0.0, 1.0 - distance_value)
            hits.append((target_id, target_type, similarity))
        return hits

    async def upsert(
        self,
        *,
        target_type: str,
        target_id: uuid.UUID,
        kind: str,
        model_name: str,
        vector: list[float],
    ) -> Embedding:
        stmt = select(Embedding).where(
            Embedding.target_type == target_type,
            Embedding.target_id == target_id,
            Embedding.kind == kind,
            Embedding.model_name == model_name,
        )
        existing = cast(Embedding | None, await self.session.scalar(stmt))
        if existing is not None:
            existing.embedding = vector
            await self.session.flush()
            return existing

        row = Embedding(
            target_type=target_type,
            target_id=target_id,
            kind=kind,
            model_name=model_name,
            embedding=vector,
        )
        self.session.add(row)
        await self.session.flush()
        return row
