"""R-SET-004 — difficulty progresses as planned."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.set_context import SetRuleContext


class SetDifficultyProgressionRule:
    code = "R-SET-004"
    severity = Severity.SHOULD

    def evaluate(self, context: SetRuleContext) -> RuleResult:
        planned = context.planned_difficulties
        if not planned:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="No planned difficulty progression",
                detail={"skipped": True},
            )

        actual = planned[: len(context.items)]
        passed = actual == sorted(actual)
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Difficulty progresses as planned"
            if passed
            else "Difficulty progression differs from plan",
            detail={"planned": list(planned), "checked": list(actual)},
        )
