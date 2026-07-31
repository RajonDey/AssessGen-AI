"""R-PASS-008 — paragraph count appropriate for planned question types."""

from __future__ import annotations

from app.domain.enums import ItemType, Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.context import PassageRuleContext
from app.modules.ielts.reading.thresholds import MIN_PARAGRAPHS_FOR_HEADING_MATCH


class PassageParagraphCountRule:
    code = "R-PASS-008"
    severity = Severity.SHOULD

    def evaluate(self, context: PassageRuleContext) -> RuleResult:
        needs_headings = ItemType.HEADING_MATCH.value in context.planned_item_types
        count = context.paragraph_count
        required = MIN_PARAGRAPHS_FOR_HEADING_MATCH if needs_headings else 1
        passed = count >= required
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                f"Paragraph count {count} sufficient for planned types"
                if passed
                else f"Paragraph count {count} below required {required} for heading match"
            ),
            detail={
                "paragraph_count": count,
                "required_min": required,
                "planned_item_types": list(context.planned_item_types),
            },
        )
