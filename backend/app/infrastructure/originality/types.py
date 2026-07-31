"""Originality check result types for infrastructure — no domain imports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OriginalityMatch:
    ngram: str
    source_document_id: str | None = None


@dataclass(frozen=True, slots=True)
class OriginalityReport:
    passed: bool
    checked_ngram_count: int = 0
    match: OriginalityMatch | None = None

    @property
    def is_blocking(self) -> bool:
        return not self.passed
