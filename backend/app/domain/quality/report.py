"""Quality report aggregation — findings, not a headline score."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult


class QualityReport(BaseModel):
    results: tuple[RuleResult, ...] = Field(default_factory=tuple)

    @property
    def failures(self) -> tuple[RuleResult, ...]:
        return tuple(r for r in self.results if not r.passed)

    @property
    def must_failures(self) -> tuple[RuleResult, ...]:
        return tuple(r for r in self.failures if r.severity == Severity.MUST)

    @property
    def should_failures(self) -> tuple[RuleResult, ...]:
        return tuple(r for r in self.failures if r.severity == Severity.SHOULD)

    @property
    def has_blocking_failures(self) -> bool:
        return bool(self.must_failures)

    @property
    def passed(self) -> bool:
        return not self.has_blocking_failures
