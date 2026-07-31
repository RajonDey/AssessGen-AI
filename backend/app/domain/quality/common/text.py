"""Text utilities for deterministic quality rules."""

from __future__ import annotations

import re
import statistics
from re import Pattern

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD_TOKEN = re.compile(r"[A-Za-z']+")
_SUBJECT_WAS_NUM = re.compile(
    (
        r"(?P<subject>the [a-z\s]{2,40}?)\s+was\s+"
        r"(?P<value>[\d,.]+(?:\.\d+)?(?:\s*(?:million|billion|percent|%))?)"
    ),
    re.IGNORECASE,
)


def plain_passage_text(body: str) -> str:
    """Strip paragraph labels (A, B, C…) from labelled passage bodies."""
    lines = body.splitlines()
    cleaned: list[str] = []
    for line in lines:
        if len(line) == 1 and line.isalpha() and line.isupper():
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def split_sentences(text: str) -> list[str]:
    normalized = plain_passage_text(text).strip()
    if not normalized:
        return []
    parts = _SENTENCE_SPLIT.split(normalized)
    return [part.strip() for part in parts if part.strip()]


def sentence_word_lengths(text: str) -> list[int]:
    return [len(_WORD_TOKEN.findall(sentence)) for sentence in split_sentences(text)]


def sentence_length_variance(text: str) -> float:
    lengths = sentence_word_lengths(text)
    if len(lengths) < 2:
        return 0.0
    return float(statistics.pvariance(lengths))


def tokenize_words(text: str) -> list[str]:
    return [match.group(0).lower() for match in _WORD_TOKEN.finditer(plain_passage_text(text))]


def find_person_pronouns(text: str, patterns: tuple[Pattern[str], ...]) -> list[str]:
    body = plain_passage_text(text).lower()
    hits: list[str] = []
    for pattern in patterns:
        if pattern.search(body):
            hits.append(pattern.pattern)
    return hits


def find_contradictory_subject_values(text: str) -> list[dict[str, str]]:
    """Detect the same subject noun phrase paired with conflicting numeric claims."""
    claims: dict[str, set[str]] = {}
    for match in _SUBJECT_WAS_NUM.finditer(plain_passage_text(text)):
        subject = " ".join(match.group("subject").lower().split())
        value = match.group("value").lower().strip()
        claims.setdefault(subject, set()).add(value)

    contradictions: list[dict[str, str]] = []
    for subject, values in claims.items():
        if len(values) > 1:
            contradictions.append(
                {
                    "subject": subject,
                    "values": ", ".join(sorted(values)),
                }
            )
    return contradictions
