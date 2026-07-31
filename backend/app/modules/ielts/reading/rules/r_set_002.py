"""R-SET-002 — question-type mix matches the plan."""

from __future__ import annotations

from collections import Counter

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.set_context import SetRuleContext


class SetTypeMixRule:
    code = "R-SET-002"
    severity = Severity.MUST

    def evaluate(self, context: SetRuleContext) -> RuleResult:
        if not context.planned_type_counts:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="No planned type counts to validate",
                detail={"skipped": True},
            )

        actual = Counter(item.item_type.value for item in context.items)
        expected = Counter(context.planned_type_counts)
        passed = actual == expected
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Question-type mix matches plan"
            if passed
            else "Question-type mix differs from plan",
            detail={"actual": dict(actual), "expected": dict(expected)},
        )
