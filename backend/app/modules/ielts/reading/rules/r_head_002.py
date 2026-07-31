"""R-HEAD-002 — mapping is one-to-one with no missing or duplicate paragraphs."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import is_heading_match, mapping_key
from app.modules.ielts.reading.item_context import ItemRuleContext


class HeadingBijectionRule:
    code = "R-HEAD-002"
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
        mapped_paragraphs = {k.upper() for k in key.values}
        mapped_headings = list(key.values.values())

        missing = sorted(labels - mapped_paragraphs)
        extra = sorted(mapped_paragraphs - labels)
        duplicate_paragraphs = len(key.values) != len(mapped_paragraphs)
        duplicate_headings = len(mapped_headings) != len(set(mapped_headings))
        passed = (
            not missing
            and not extra
            and not duplicate_paragraphs
            and not duplicate_headings
            and len(key.values) == len(labels)
        )

        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Heading mapping is one-to-one"
            if passed
            else "Heading mapping is not one-to-one",
            detail={
                "missing_paragraphs": missing,
                "unknown_paragraphs": extra,
                "duplicate_paragraphs": duplicate_paragraphs,
                "duplicate_headings": duplicate_headings,
            },
        )
