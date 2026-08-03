"""IELTS Writing format bounds — Phase 1C (Task 2 only)."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.ielts.writing.schemas import WritingTask2Type


@dataclass(frozen=True, slots=True)
class WritingSpec:
    task2_min_words: int = 250
    phase_1c_question_types: tuple[WritingTask2Type, ...] = (
        "opinion",
        "discussion",
        "problem_solution",
        "advantages_disadvantages",
        "two_part",
    )
