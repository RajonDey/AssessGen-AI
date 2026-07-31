"""R-ITEM-003 — answer key is well-formed for the item type."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import (
    exact_key,
    is_completion_type,
    is_heading_match,
    mapping_key,
)
from app.modules.ielts.reading.item_context import ItemRuleContext


class ItemAnswerKeyWellFormedRule:
    code = "R-ITEM-003"
    severity = Severity.MUST

    def evaluate(self, context: ItemRuleContext) -> RuleResult:
        item = context.item
        item_type = item.item_type

        if is_completion_type(item_type):
            key = exact_key(item)
            passed = key is not None and bool(key.values) and all(v.strip() for v in key.values)
            return RuleResult(
                rule_code=self.code,
                passed=passed,
                severity=self.severity,
                message="Exact answer key is well-formed"
                if passed
                else "Completion item requires exact answer key",
                detail={"key_type": "exact"},
            )

        if is_heading_match(item_type):
            key = mapping_key(item)
            passed = (
                key is not None
                and bool(key.values)
                and all(k.strip() and v.strip() for k, v in key.values.items())
            )
            return RuleResult(
                rule_code=self.code,
                passed=passed,
                severity=self.severity,
                message="Mapping answer key is well-formed"
                if passed
                else "Heading match requires mapping key",
                detail={"key_type": "mapping", "mapping_size": len(key.values) if key else 0},
            )

        return RuleResult(
            rule_code=self.code,
            passed=False,
            severity=self.severity,
            message=f"Unsupported item type: {item_type}",
            detail={"item_type": str(item_type)},
        )
