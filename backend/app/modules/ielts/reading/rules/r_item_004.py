"""R-ITEM-004 — evidence span exists and offsets lie inside the passage."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import is_completion_type, is_heading_match
from app.modules.ielts.reading.item_context import ItemRuleContext


class ItemEvidenceBoundsRule:
    code = "R-ITEM-004"
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
        body_len = len(context.body)
        if evidence is None:
            return RuleResult(
                rule_code=self.code,
                passed=False,
                severity=self.severity,
                message="Evidence span is required",
                detail={},
            )

        labels = {p.label.upper() for p in context.passage.paragraphs}
        label_ok = evidence.paragraph.strip().upper() in labels
        offsets_ok = 0 <= evidence.start < evidence.end <= body_len
        passed = label_ok and offsets_ok
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Evidence span is within passage bounds"
            if passed
            else "Evidence span is invalid",
            detail={
                "paragraph": evidence.paragraph,
                "start": evidence.start,
                "end": evidence.end,
                "body_length": body_len,
                "label_ok": label_ok,
            },
        )
