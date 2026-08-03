"""Pydantic shapes for IELTS Writing Task 2 (Phase 1C)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

WritingTask2Type = Literal[
    "opinion",
    "discussion",
    "problem_solution",
    "advantages_disadvantages",
    "two_part",
]


class WritingTask2Prompt(BaseModel):
    task: Literal[2] = 2
    question_type: WritingTask2Type
    topic: str = Field(min_length=1)
    prompt: str = Field(min_length=50)
    word_count_instruction: str = Field(
        default="Write at least 250 words.",
        min_length=1,
    )
