"""Vocabulary frequency helpers — Zipf bands via wordfreq."""

from __future__ import annotations

import wordfreq

from app.domain.quality.common.text import tokenize_words


def rare_word_ratio(text: str, *, zipf_threshold: float, lang: str = "en") -> float:
    tokens = tokenize_words(text)
    if not tokens:
        return 0.0
    rare = sum(1 for token in tokens if wordfreq.zipf_frequency(token, lang) < zipf_threshold)
    return rare / len(tokens)
