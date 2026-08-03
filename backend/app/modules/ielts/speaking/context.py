"""Evaluation context for Speaking quality rules."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.ielts.speaking.schemas import SpeakingPart1And2


class SpeakingRuleContext(BaseModel):
    content: SpeakingPart1And2
    target_band: float = Field(default=7.0, ge=5.0, le=9.0)

    @property
    def part1_topics(self):
        return self.content.part1_topics

    @property
    def part2(self):
        return self.content.part2
