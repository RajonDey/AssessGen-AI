"""R-PASS-001 — word count within module bounds."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.context import PassageRuleContext


class PassageWordCountRule:
    code = "R-PASS-001"
    severity = Severity.MUST

    def evaluate(self, context: PassageRuleContext) -> RuleResult:
        count = context.word_count()
        passed = context.word_count_min <= count <= context.word_count_max
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                f"Word count {count} is within {context.word_count_min}–{context.word_count_max}"
                if passed
                else (
                    f"Word count {count} is outside "
                    f"{context.word_count_min}–{context.word_count_max}"
                )
            ),
            detail={
                "word_count": count,
                "min": context.word_count_min,
                "max": context.word_count_max,
            },
        )
