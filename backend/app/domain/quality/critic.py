"""LLM critic output models — structured findings only, no score."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.enums import FindingCategory, Severity


class CriticFinding(BaseModel):
    category: FindingCategory
    target: str = Field(min_length=1)
    severity: Severity
    explanation: str = Field(min_length=1)
    suggested_fix: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class CriticOutput(BaseModel):
    findings: list[CriticFinding] = Field(default_factory=list)

    @property
    def blocking_findings(self) -> tuple[CriticFinding, ...]:
        return tuple(f for f in self.findings if f.severity == Severity.MUST)

    @property
    def has_blocking_findings(self) -> bool:
        return bool(self.blocking_findings)
