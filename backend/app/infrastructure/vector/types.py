"""Dedup result types for infrastructure — no domain imports."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SimilarityHit:
    target_id: UUID
    target_type: str
    similarity: float


@dataclass(frozen=True, slots=True)
class DedupReport:
    passed: bool
    threshold: float
    hits: tuple[SimilarityHit, ...] = ()

    @property
    def is_blocking(self) -> bool:
        return not self.passed
