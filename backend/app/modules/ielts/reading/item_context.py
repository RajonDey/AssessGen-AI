"""Item-level evaluation context for Reading quality rules."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.ielts.reading.schemas import ReadingItem, ReadingPassage


class ItemRuleContext(BaseModel):
    passage: ReadingPassage
    item: ReadingItem
    item_index: int = Field(default=0, ge=0)
    all_items: tuple[ReadingItem, ...] = Field(default_factory=tuple)
    estimated_time_seconds: int | None = Field(default=None, ge=0)

    @property
    def body(self) -> str:
        return self.passage.body
