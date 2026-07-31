"""Originality check result models — pure domain."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OriginalityMatch(BaseModel):
    ngram: str = Field(min_length=1)
    source_document_id: str | None = None


class OriginalityReport(BaseModel):
    passed: bool
    match: OriginalityMatch | None = None
    checked_ngram_count: int = Field(default=0, ge=0)

    @property
    def is_blocking(self) -> bool:
        return not self.passed
