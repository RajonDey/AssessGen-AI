"""Set-level evaluation context for Reading quality rules."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.ielts.reading.schemas import ReadingItem, ReadingPassage


class SetRuleContext(BaseModel):
    passage: ReadingPassage
    items: tuple[ReadingItem, ...] = Field(default_factory=tuple)
    expected_item_count: int = Field(default=0, ge=0)
    planned_item_types: tuple[str, ...] = Field(default_factory=tuple)
    planned_type_counts: dict[str, int] = Field(default_factory=dict)
    planned_difficulties: tuple[float, ...] = Field(default_factory=tuple)

    @property
    def body(self) -> str:
        return self.passage.body

    @property
    def paragraph_count(self) -> int:
        return len(self.passage.paragraphs)
