"""Pydantic shapes for IELTS Speaking (Phase 1C — Part 1 + Part 2)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SpeakingPart1Topic(BaseModel):
    name: str = Field(min_length=1)
    questions: list[str] = Field(min_length=3, max_length=4)


class SpeakingPart2CueCard(BaseModel):
    topic: str = Field(min_length=1)
    bullets: list[str] = Field(min_length=3, max_length=3)
    explain_prompt: str = Field(min_length=1)


class SpeakingPart1And2(BaseModel):
    part1_topics: list[SpeakingPart1Topic] = Field(min_length=3, max_length=3)
    part2: SpeakingPart2CueCard
