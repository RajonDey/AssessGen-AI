"""Passage evaluation context for rules."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.ielts.reading.schemas import ReadingPassage


class PassageRuleContext(BaseModel):
    passage: ReadingPassage
    target_band: float = Field(default=7.0, ge=0.0, le=9.0)
    planned_item_types: tuple[str, ...] = Field(default_factory=tuple)
    word_count_min: int = Field(default=700, ge=1)
    word_count_max: int = Field(default=1000, ge=1)

    @property
    def body(self) -> str:
        return self.passage.body

    @property
    def paragraph_count(self) -> int:
        return len(self.passage.paragraphs)

    def word_count(self) -> int:
        return len(self.body.split())
