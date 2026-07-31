"""IELTS exam-wide constants."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import ItemType


@dataclass(frozen=True, slots=True)
class IELTSSpec:
    exam: str = "ielts"
    academic_reading_passages: int = 3
    academic_reading_questions: int = 40
    academic_reading_minutes: int = 60


PHASE_1B_READING_TYPES: tuple[ItemType, ...] = (
    ItemType.SENTENCE_COMPLETION,
    ItemType.SUMMARY_COMPLETION,
    ItemType.SHORT_ANSWER,
    ItemType.NOTE_COMPLETION,
    ItemType.HEADING_MATCH,
)
