"""R-HEAD-003 — every mapped paragraph label exists in the passage."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import is_heading_match, mapping_key
from app.modules.ielts.reading.item_context import ItemRuleContext


class HeadingParagraphExistsRule:
    code = "R-HEAD-003"
    severity = Severity.MUST

    def evaluate(self, context: ItemRuleContext) -> RuleResult:
        if not is_heading_match(context.item.item_type):
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Not a heading match item",
                detail={"skipped": True},
            )

        key = mapping_key(context.item)
        if key is None:
            return RuleResult(
                rule_code=self.code,
                passed=False,
                severity=self.severity,
                message="Missing mapping key",
                detail={},
            )

        labels = {p.label.upper() for p in context.passage.paragraphs}
        invalid = [paragraph for paragraph in key.values if paragraph.upper() not in labels]
        passed = not invalid
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="All mapped paragraphs exist"
            if passed
            else "Unknown paragraph labels in mapping",
            detail={"invalid_paragraphs": invalid, "known_labels": sorted(labels)},
        )
