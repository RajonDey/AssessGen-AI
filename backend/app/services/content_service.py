"""Content bank application service."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Item, ItemVersion, Passage, PassageVersion
from app.infrastructure.db.repositories.content_repository import ContentRepository
from app.schemas.content import (
    ItemDetail,
    ItemListResponse,
    ItemSummary,
    PassageDetail,
    PassageListResponse,
    PassageSummary,
)


class ContentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ContentRepository(session)

    async def list_passages(self, organization_id: uuid.UUID) -> PassageListResponse:
        rows = await self.repo.list_passages(organization_id)
        return PassageListResponse(items=[self._passage_summary(row) for row in rows])

    async def get_passage(
        self,
        passage_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
    ) -> PassageDetail | None:
        row = await self.repo.get_passage(passage_id, organization_id=organization_id)
        if row is None:
            return None
        passage, version = row
        summary = self._passage_summary((passage, version))
        return PassageDetail(
            **summary.model_dump(),
            body=version.body if version else None,
            paragraphs=version.paragraphs if version else None,
        )

    async def list_items(self, organization_id: uuid.UUID) -> ItemListResponse:
        rows = await self.repo.list_items(organization_id)
        return ItemListResponse(items=[self._item_summary(row) for row in rows])

    async def get_item(
        self,
        item_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
    ) -> ItemDetail | None:
        row = await self.repo.get_item(item_id, organization_id=organization_id)
        if row is None:
            return None
        item, version = row
        summary = self._item_summary((item, version))
        return ItemDetail(
            **summary.model_dump(),
            instructions=version.instructions if version else None,
            options=version.options if version else None,
            answer_key=version.answer_key if version else None,
            evidence=version.evidence if version else None,
        )

    @staticmethod
    def _passage_summary(row: tuple[Passage, PassageVersion | None]) -> PassageSummary:
        passage, version = row
        target_band = float(version.target_band) if version and version.target_band else None
        return PassageSummary(
            id=passage.id,
            status=passage.status,
            title=version.title if version else None,
            word_count=version.word_count if version else None,
            target_band=target_band,
            created_at=passage.created_at,
        )

    @staticmethod
    def _item_summary(row: tuple[Item, ItemVersion | None]) -> ItemSummary:
        item, version = row
        return ItemSummary(
            id=item.id,
            status=item.status,
            item_type=item.item_type,
            stem=version.stem if version else None,
            passage_id=item.passage_id,
            sequence_no=version.sequence_no if version else None,
            created_at=item.created_at,
        )
