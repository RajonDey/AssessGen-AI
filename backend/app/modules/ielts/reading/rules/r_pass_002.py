"""R-PASS-002 — paragraph labels sequential and unique."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.context import PassageRuleContext


class PassageParagraphLabelsRule:
    code = "R-PASS-002"
    severity = Severity.MUST

    def evaluate(self, context: PassageRuleContext) -> RuleResult:
        labels = [p.label.upper() for p in context.passage.paragraphs]
        expected = [chr(ord("A") + i) for i in range(len(labels))]
        unique = len(labels) == len(set(labels))
        sequential = labels == expected
        passed = unique and sequential
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                "Paragraph labels are sequential and unique"
                if passed
                else f"Paragraph labels invalid: found {labels}, expected {expected}"
            ),
            detail={
                "labels": labels,
                "expected": expected,
                "unique": unique,
                "sequential": sequential,
            },
        )
