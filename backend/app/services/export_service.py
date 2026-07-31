"""Export approved reading content as JSON bundles."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.content_repository import ContentRepository


class ExportError(Exception):
    """Export could not be produced."""


class ExportService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ContentRepository(session)

    async def export_reading_run(
        self,
        *,
        run_id: uuid.UUID,
        organization_id: uuid.UUID,
        publish: bool = True,
    ) -> dict[str, Any]:
        passages = await self.repo.list_passages_by_run(run_id, organization_id=organization_id)
        if not passages:
            raise ExportError(f"No passages found for run {run_id}")

        bundle_passages: list[dict[str, Any]] = []
        for passage, version in passages:
            if passage.status not in {"approved", "published"}:
                raise ExportError(
                    f"Passage {passage.id} is {passage.status}; approve before export"
                )
            items = await self.repo.list_items_for_passage(
                passage.id,
                organization_id=organization_id,
            )
            bundle_passages.append(
                {
                    "passage_id": str(passage.id),
                    "status": passage.status,
                    "title": version.title,
                    "body": version.body,
                    "paragraphs": version.paragraphs,
                    "word_count": version.word_count,
                    "target_band": float(version.target_band) if version.target_band else None,
                    "items": [
                        {
                            "item_id": str(item.id),
                            "item_type": item.item_type,
                            "status": item.status,
                            "sequence_no": item_version.sequence_no,
                            "stem": item_version.stem,
                            "instructions": item_version.instructions,
                            "options": item_version.options,
                            "answer_key": item_version.answer_key,
                            "evidence": item_version.evidence,
                        }
                        for item, item_version in items
                    ],
                }
            )
            if publish:
                await self.repo.publish_passage_set(passage.id, organization_id=organization_id)

        return {
            "format": "assessgen.reading.v1",
            "run_id": str(run_id),
            "module": "reading",
            "passage_count": len(bundle_passages),
            "question_count": sum(len(p["items"]) for p in bundle_passages),
            "passages": bundle_passages,
        }
