"""Content bank API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PassageSummary(BaseModel):
    id: UUID
    module: str
    status: str
    title: str | None = None
    word_count: int | None = None
    target_band: float | None = None
    created_at: datetime


class PassageDetail(PassageSummary):
    body: str | None = None
    paragraphs: list[dict] | None = None


class PassageListResponse(BaseModel):
    items: list[PassageSummary]


class ItemSummary(BaseModel):
    id: UUID
    module: str
    status: str
    item_type: str
    stem: str | None = None
    passage_id: UUID | None = None
    sequence_no: int | None = None
    created_at: datetime


class ItemDetail(ItemSummary):
    instructions: str | None = None
    options: list[str] | None = None
    answer_key: dict | None = None
    evidence: dict | None = None


class ItemListResponse(BaseModel):
    items: list[ItemSummary]
