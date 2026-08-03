"""Shared helpers for IELTS Reading quality rules."""

from __future__ import annotations

import re
from re import Pattern

from app.domain.enums import ItemType
from app.modules.ielts.reading.schemas import (
    AnswerKeyExact,
    AnswerKeyMapping,
    EvidenceSpan,
    ReadingItem,
    ReadingPassage,
)

COMPLETION_TYPES: frozenset[ItemType] = frozenset(
    {
        ItemType.SENTENCE_COMPLETION,
        ItemType.SUMMARY_COMPLETION,
        ItemType.SHORT_ANSWER,
        ItemType.NOTE_COMPLETION,
    }
)

# Standard IELTS instruction phrasings for completion items.
LEGAL_WORD_LIMIT_PATTERNS: tuple[Pattern[str], ...] = (
    re.compile(r"NO MORE THAN TWO WORDS AND/OR A NUMBER", re.IGNORECASE),
    re.compile(r"NO MORE THAN THREE WORDS AND/OR A NUMBER", re.IGNORECASE),
    re.compile(r"NO MORE THAN ONE WORD AND/OR A NUMBER", re.IGNORECASE),
    re.compile(r"NO MORE THAN THREE WORDS", re.IGNORECASE),
    re.compile(r"NO MORE THAN TWO WORDS", re.IGNORECASE),
    re.compile(r"ONE WORD ONLY", re.IGNORECASE),
    re.compile(r"ONE WORD AND/OR A NUMBER", re.IGNORECASE),
)

WORD_LIMIT_FROM_INSTRUCTIONS: tuple[tuple[Pattern[str], int], ...] = (
    (re.compile(r"NO MORE THAN THREE WORDS", re.IGNORECASE), 3),
    (re.compile(r"NO MORE THAN TWO WORDS", re.IGNORECASE), 2),
    (re.compile(r"NO MORE THAN ONE WORD", re.IGNORECASE), 1),
    (re.compile(r"ONE WORD ONLY", re.IGNORECASE), 1),
)

FUNCTION_WORDS: frozenset[str] = frozenset(
    {"a", "an", "the", "of", "and", "in", "on", "at", "to", "for", "with", "by", "as", "or"}
)

GAP_PATTERN = re.compile(r"_{3,}|\.{3,}|…+|(\[\s*gap\s*\])", re.IGNORECASE)

STEM_MIN_LENGTH = 10

ITEM_TIME_SECONDS: dict[ItemType, tuple[int, int]] = {
    ItemType.SENTENCE_COMPLETION: (45, 120),
    ItemType.SUMMARY_COMPLETION: (60, 180),
    ItemType.SHORT_ANSWER: (45, 120),
    ItemType.NOTE_COMPLETION: (60, 180),
    ItemType.HEADING_MATCH: (90, 240),
}


def is_completion_type(item_type: ItemType) -> bool:
    return item_type in COMPLETION_TYPES


def is_heading_match(item_type: ItemType) -> bool:
    return item_type == ItemType.HEADING_MATCH


def primary_answer(item: ReadingItem) -> str | None:
    key = item.answer_key
    if isinstance(key, AnswerKeyExact):
        return key.values[0] if key.values else None
    return None


def parse_word_limit(instructions: str | None) -> int | None:
    if not instructions:
        return None
    for pattern, limit in WORD_LIMIT_FROM_INSTRUCTIONS:
        if pattern.search(instructions):
            return limit
    return None


def instructions_are_legal(instructions: str | None) -> bool:
    if not instructions:
        return False
    return any(pattern.search(instructions) for pattern in LEGAL_WORD_LIMIT_PATTERNS)


def count_answer_words(answer: str) -> int:
    tokens = re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?", answer.strip())
    return len(tokens)


def find_verbatim_match(
    body: str, answer: str, *, case_sensitive: bool = False
) -> dict[str, int | str] | None:
    if not answer.strip():
        return None
    haystack = body if case_sensitive else body.lower()
    needle = answer if case_sensitive else answer.lower()
    index = haystack.find(needle)
    if index < 0:
        return None
    return {"start": index, "end": index + len(answer), "quote": body[index : index + len(answer)]}


def paragraph_text_ranges(passage: ReadingPassage) -> list[tuple[str, int, int]]:
    """Return each paragraph label with start/end offsets into passage.body text."""
    offset = 0
    ranges: list[tuple[str, int, int]] = []
    for index, paragraph in enumerate(passage.paragraphs):
        prefix = f"{paragraph.label}\n"
        start = offset + len(prefix)
        end = start + len(paragraph.text)
        ranges.append((paragraph.label, start, end))
        offset = end + (2 if index < len(passage.paragraphs) - 1 else 0)
    return ranges


def paragraph_label_at_offset(passage: ReadingPassage, offset: int) -> str:
    ranges = paragraph_text_ranges(passage)
    for label, start, end in ranges:
        if start <= offset < end:
            return label
    if ranges:
        return ranges[-1][0]
    msg = "Passage has no paragraphs"
    raise ValueError(msg)


def resolve_evidence_span(
    passage: ReadingPassage,
    answer: str,
    *,
    case_sensitive: bool = False,
) -> EvidenceSpan | None:
    """Locate a verbatim answer in passage.body and return a consistent evidence span."""
    match = find_verbatim_match(passage.body, answer, case_sensitive=case_sensitive)
    if match is None:
        return None
    start = int(match["start"])
    end = int(match["end"])
    quote = str(match["quote"])
    return EvidenceSpan(
        paragraph=paragraph_label_at_offset(passage, start),
        start=start,
        end=end,
        quote=quote,
    )


def normalize_item_evidence(passage: ReadingPassage, item: ReadingItem) -> ReadingItem:
    """Replace LLM offsets with deterministic evidence derived from the answer key."""
    if not is_completion_type(item.item_type):
        return item
    key = exact_key(item)
    if key is None or not key.values:
        return item
    resolved = resolve_evidence_span(
        passage,
        key.values[0],
        case_sensitive=key.case_sensitive,
    )
    if resolved is None:
        return item
    return item.model_copy(update={"evidence": resolved})


def stem_contains_answer(stem: str, answer: str) -> bool:
    if not answer.strip():
        return False
    return answer.lower() in stem.lower()


def fill_gap(stem: str, answer: str) -> str:
    return GAP_PATTERN.sub(answer, stem, count=1)


def paragraph_label_order(label: str) -> int:
    label = label.strip().upper()
    if len(label) == 1 and label.isalpha():
        return ord(label) - ord("A")
    return -1


def mapping_key(item: ReadingItem) -> AnswerKeyMapping | None:
    key = item.answer_key
    if isinstance(key, AnswerKeyMapping):
        return key
    return None


def exact_key(item: ReadingItem) -> AnswerKeyExact | None:
    key = item.answer_key
    if isinstance(key, AnswerKeyExact):
        return key
    return None
