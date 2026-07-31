"""R-ITEM-005 — quoted evidence matches passage text at offsets."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import is_completion_type, is_heading_match
from app.modules.ielts.reading.item_context import ItemRuleContext


class ItemEvidenceQuoteMatchRule:
    code = "R-ITEM-005"
    severity = Severity.MUST

    def evaluate(self, context: ItemRuleContext) -> RuleResult:
        if is_heading_match(context.item.item_type):
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Heading match uses mapping key, not evidence span",
                detail={"skipped": True},
            )

        if not is_completion_type(context.item.item_type):
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Not applicable to this item type",
                detail={"skipped": True},
            )

        evidence = context.item.evidence
        if evidence is None:
            return RuleResult(
                rule_code=self.code,
                passed=False,
                severity=self.severity,
                message="Evidence span is required",
                detail={},
            )

        slice_text = context.body[evidence.start : evidence.end]
        passed = slice_text == evidence.quote
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Evidence quote matches passage slice" if passed else "Evidence quote mismatch",
            detail={
                "expected": evidence.quote,
                "actual": slice_text,
                "start": evidence.start,
                "end": evidence.end,
            },
        )
