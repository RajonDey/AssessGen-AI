"""Rule protocol and result types — pure domain, no I/O."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.domain.enums import Severity


class RuleResult(BaseModel):
    """Outcome of a single deterministic rule evaluation."""

    rule_code: str
    passed: bool
    severity: Severity
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class Rule(Protocol):
    """A deterministic quality rule over a typed context object."""

    code: str
    severity: Severity

    def evaluate(self, context: Any) -> RuleResult: ...
