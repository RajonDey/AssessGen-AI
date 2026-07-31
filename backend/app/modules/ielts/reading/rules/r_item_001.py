"""R-ITEM-001 — stem is non-empty and above minimum length."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import STEM_MIN_LENGTH
from app.modules.ielts.reading.item_context import ItemRuleContext


class ItemStemLengthRule:
    code = "R-ITEM-001"
    severity = Severity.MUST

    def evaluate(self, context: ItemRuleContext) -> RuleResult:
        stem = context.item.stem.strip()
        length = len(stem)
        passed = length >= STEM_MIN_LENGTH
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                f"Stem length {length} meets minimum {STEM_MIN_LENGTH}"
                if passed
                else f"Stem length {length} is below minimum {STEM_MIN_LENGTH}"
            ),
            detail={"stem_length": length, "minimum": STEM_MIN_LENGTH},
        )
