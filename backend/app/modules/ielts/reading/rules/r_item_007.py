"""R-ITEM-007 — estimated time within plausible range for the item type."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import ITEM_TIME_SECONDS
from app.modules.ielts.reading.item_context import ItemRuleContext


class ItemEstimatedTimeRule:
    code = "R-ITEM-007"
    severity = Severity.SHOULD

    def evaluate(self, context: ItemRuleContext) -> RuleResult:
        bounds = ITEM_TIME_SECONDS.get(context.item.item_type)
        if bounds is None or context.estimated_time_seconds is None:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="No time estimate to validate",
                detail={"skipped": True},
            )

        low, high = bounds
        seconds = context.estimated_time_seconds
        passed = low <= seconds <= high
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                f"Estimated time {seconds}s is within {low}–{high}s"
                if passed
                else f"Estimated time {seconds}s is outside {low}–{high}s"
            ),
            detail={"seconds": seconds, "low": low, "high": high},
        )
