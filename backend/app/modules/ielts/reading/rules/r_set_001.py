"""R-SET-001 — item count matches the request."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.set_context import SetRuleContext


class SetItemCountRule:
    code = "R-SET-001"
    severity = Severity.MUST

    def evaluate(self, context: SetRuleContext) -> RuleResult:
        actual = len(context.items)
        expected = context.expected_item_count
        passed = expected == 0 or actual == expected
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                f"Item count {actual} matches expected {expected}"
                if passed
                else f"Item count {actual} does not match expected {expected}"
            ),
            detail={"actual": actual, "expected": expected},
        )
