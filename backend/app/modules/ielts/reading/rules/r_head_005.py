"""R-HEAD-005 — no heading repeats a paragraph opening verbatim."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import is_heading_match
from app.modules.ielts.reading.item_context import ItemRuleContext

OPENING_WORDS = 5


class HeadingNoOpeningCopyRule:
    code = "R-HEAD-005"
    severity = Severity.SHOULD

    def evaluate(self, context: ItemRuleContext) -> RuleResult:
        if not is_heading_match(context.item.item_type):
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Not a heading match item",
                detail={"skipped": True},
            )

        matches: list[dict[str, str]] = []
        for heading in context.item.options:
            heading_words = heading.lower().split()[:OPENING_WORDS]
            heading_prefix = " ".join(heading_words)
            for paragraph in context.passage.paragraphs:
                opening = " ".join(paragraph.text.lower().split()[:OPENING_WORDS])
                if heading_prefix and heading_prefix == opening:
                    matches.append({"heading": heading, "paragraph": paragraph.label})

        passed = not matches
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Headings do not copy paragraph openings"
            if passed
            else "Heading copies paragraph opening",
            detail={"matches": matches},
        )
