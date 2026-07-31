"""Readability helpers — Flesch-Kincaid via textstat."""

from __future__ import annotations

import textstat

from app.domain.quality.common.text import plain_passage_text


def flesch_kincaid_grade(text: str) -> float:
    cleaned = plain_passage_text(text)
    if not cleaned.split():
        return 0.0
    return float(textstat.flesch_kincaid_grade(cleaned))
