"""8-gram shingle utilities for originality checking."""

from __future__ import annotations

import hashlib
import re

_NGRAM_SIZE = 8
_NORMALIZE_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_for_ngrams(text: str) -> str:
    lowered = text.lower()
    cleaned = _NORMALIZE_NON_ALNUM.sub(" ", lowered)
    return " ".join(cleaned.split())


def word_tokens(text: str) -> tuple[str, ...]:
    normalized = normalize_for_ngrams(text)
    if not normalized:
        return ()
    return tuple(normalized.split())


def build_ngrams(text: str, *, size: int = _NGRAM_SIZE) -> frozenset[str]:
    tokens = word_tokens(text)
    if len(tokens) < size:
        return frozenset()
    return frozenset(
        " ".join(tokens[index : index + size]) for index in range(len(tokens) - size + 1)
    )


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_for_ngrams(text).encode()).hexdigest()


def find_forbidden_overlap(
    text: str,
    forbidden: frozenset[str],
    *,
    allowed: frozenset[str] | None = None,
    size: int = _NGRAM_SIZE,
) -> str | None:
    generated = build_ngrams(text, size=size)
    permitted = allowed or frozenset()
    for ngram in generated:
        if ngram in forbidden and ngram not in permitted:
            return ngram
    return None
