"""R-HEAD-001 — headings count is at least paragraph count (distractors required)."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import is_heading_match
from app.modules.ielts.reading.item_context import ItemRuleContext


class HeadingDistractorCountRule:
    code = "R-HEAD-001"
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

        paragraph_count = len(context.passage.paragraphs)
        heading_count = len(context.item.options)
        passed = heading_count >= paragraph_count
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                f"{heading_count} headings for {paragraph_count} paragraphs"
                if passed
                else f"Need at least {paragraph_count} headings, got {heading_count}"
            ),
            detail={"headings": heading_count, "paragraphs": paragraph_count},
        )
