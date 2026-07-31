"""R-SET-003 — order-dependent items follow passage order."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import paragraph_label_order
from app.modules.ielts.reading.set_context import SetRuleContext


class SetPassageOrderRule:
    code = "R-SET-003"
    severity = Severity.SHOULD

    def evaluate(self, context: SetRuleContext) -> RuleResult:
        positions: list[int] = []
        for item in context.items:
            if item.evidence is None:
                continue
            positions.append(paragraph_label_order(item.evidence.paragraph))

        if len(positions) < 2:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Not enough evidence spans to check order",
                detail={"skipped": True},
            )

        passed = positions == sorted(positions)
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Items follow passage order" if passed else "Items are out of passage order",
            detail={"positions": positions},
        )
