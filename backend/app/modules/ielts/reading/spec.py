"""Academic Reading format bounds."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.ielts.spec import PHASE_1B_READING_TYPES


@dataclass(frozen=True, slots=True)
class AcademicReadingSpec:
    variant: str = "academic"
    passage_count: int = 3
    questions_per_test: int = 40
    questions_per_passage_min: int = 13
    questions_per_passage_max: int = 14
    passage_word_count_min: int = 700
    passage_word_count_max: int = 1000
    phase_1_item_types: tuple[str, ...] = field(
        default_factory=lambda: tuple(t.value for t in PHASE_1B_READING_TYPES)
    )
