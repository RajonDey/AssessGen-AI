"""Passage and item persistence and bank queries."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.infrastructure.db.models import Item, ItemVersion, Passage, PassageVersion
from app.infrastructure.originality.ngrams import content_hash


class ContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def persist_reading_set(
        self,
        *,
        organization_id: uuid.UUID,
        run_id: uuid.UUID,
        title: str,
        body: str,
        paragraphs: list[dict[str, object]],
        word_count: int,
        items: list[dict[str, object]],
        target_band: float,
        status: str = "awaiting_review",
    ) -> tuple[uuid.UUID, uuid.UUID, tuple[uuid.UUID, ...]]:
        passage_row = Passage(
            id=uuid.uuid4(),
            organization_id=organization_id,
            module="reading",
            status=status,
        )
        self.session.add(passage_row)
        await self.session.flush()

        passage_version = PassageVersion(
            id=uuid.uuid4(),
            passage_id=passage_row.id,
            version_no=0,
            content_hash=content_hash(body),
            title=title,
            body=body,
            paragraphs=paragraphs,
            word_count=word_count,
            target_band=Decimal(str(target_band)),
            readability={"source": "generated"},
            organization_id=organization_id,
            created_by_run_id=run_id,
        )
        self.session.add(passage_version)
        await self.session.flush()
        passage_row.current_version_id = passage_version.id

        item_version_ids: list[uuid.UUID] = []
        for sequence_no, item in enumerate(items, start=1):
            item_row = Item(
                id=uuid.uuid4(),
                organization_id=organization_id,
                module="reading",
                item_type=str(item["item_type"]),
                passage_id=passage_row.id,
                status=status,
            )
            self.session.add(item_row)
            await self.session.flush()

            item_version = ItemVersion(
                id=uuid.uuid4(),
                item_id=item_row.id,
                version_no=0,
                content_hash=content_hash(str(item["stem"])),
                stem=str(item["stem"]),
                instructions=item.get("instructions"),
                options=item.get("options") or None,
                answer_key=item["answer_key"],
                evidence=item.get("evidence"),
                sequence_no=sequence_no,
                target_band=Decimal(str(target_band)),
                created_by_run_id=run_id,
            )
            self.session.add(item_version)
            await self.session.flush()
            item_row.current_version_id = item_version.id
            item_version_ids.append(item_version.id)

        await self.session.flush()
        return passage_row.id, passage_version.id, tuple(item_version_ids)

    async def list_passages(
        self,
        organization_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[tuple[Passage, PassageVersion | None]]:
        version = aliased(PassageVersion)
        stmt = (
            select(Passage, version)
            .outerjoin(version, Passage.current_version_id == version.id)
            .where(Passage.organization_id == organization_id)
            .order_by(Passage.created_at.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows]

    async def get_passage(
        self,
        passage_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
    ) -> tuple[Passage, PassageVersion | None] | None:
        version = aliased(PassageVersion)
        stmt = (
            select(Passage, version)
            .outerjoin(version, Passage.current_version_id == version.id)
            .where(Passage.id == passage_id, Passage.organization_id == organization_id)
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None
        return row[0], row[1]

    async def list_items(
        self,
        organization_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[tuple[Item, ItemVersion | None]]:
        version = aliased(ItemVersion)
        stmt = (
            select(Item, version)
            .outerjoin(version, Item.current_version_id == version.id)
            .where(Item.organization_id == organization_id)
            .order_by(Item.created_at.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows]

    async def get_item(
        self,
        item_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
    ) -> tuple[Item, ItemVersion | None] | None:
        version = aliased(ItemVersion)
        stmt = (
            select(Item, version)
            .outerjoin(version, Item.current_version_id == version.id)
            .where(Item.id == item_id, Item.organization_id == organization_id)
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None
        return row[0], row[1]

    async def approve_passage_set(
        self,
        passage_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
    ) -> None:
        passage = await self.session.get(Passage, passage_id)
        if passage is None or passage.organization_id != organization_id:
            msg = f"Passage {passage_id} not found"
            raise ValueError(msg)
        if passage.current_version_id is None:
            msg = f"Passage {passage_id} has no current version"
            raise ValueError(msg)

        passage.status = "approved"
        await self.session.execute(
            update(Item)
            .where(Item.passage_id == passage_id, Item.organization_id == organization_id)
            .values(status="approved")
        )
        await self.session.flush()

    async def list_passages_by_run(
        self,
        run_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
    ) -> list[tuple[Passage, PassageVersion]]:
        version = aliased(PassageVersion)
        stmt = (
            select(Passage, version)
            .join(version, Passage.current_version_id == version.id)
            .where(
                Passage.organization_id == organization_id,
                version.created_by_run_id == run_id,
            )
            .order_by(Passage.created_at.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows]

    async def list_items_for_passage(
        self,
        passage_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
    ) -> list[tuple[Item, ItemVersion]]:
        version = aliased(ItemVersion)
        stmt = (
            select(Item, version)
            .join(version, Item.current_version_id == version.id)
            .where(Item.passage_id == passage_id, Item.organization_id == organization_id)
            .order_by(version.sequence_no.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows]

    async def publish_passage_set(
        self,
        passage_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
    ) -> None:
        passage = await self.session.get(Passage, passage_id)
        if passage is None or passage.organization_id != organization_id:
            msg = f"Passage {passage_id} not found"
            raise ValueError(msg)
        if passage.status != "approved":
            msg = f"Passage {passage_id} must be approved before publish"
            raise ValueError(msg)

        passage.status = "published"
        await self.session.execute(
            update(Item)
            .where(
                Item.passage_id == passage_id,
                Item.organization_id == organization_id,
                Item.status == "approved",
            )
            .values(status="published")
        )
        await self.session.flush()
