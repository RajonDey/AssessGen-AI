"""Dedup similarity result models — pure domain."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class SimilarityHit(BaseModel):
    target_id: UUID
    target_type: str
    similarity: float = Field(ge=0.0, le=1.0)


class DedupReport(BaseModel):
    passed: bool
    hits: tuple[SimilarityHit, ...] = Field(default_factory=tuple)
    threshold: float = Field(ge=0.0, le=1.0)

    @property
    def is_blocking(self) -> bool:
        return not self.passed
