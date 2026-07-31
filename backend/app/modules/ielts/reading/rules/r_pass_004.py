"""R-PASS-004 — readability within target band range (Flesch-Kincaid)."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.common.readability import flesch_kincaid_grade
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.bands import fk_grade_range
from app.modules.ielts.reading.context import PassageRuleContext


class PassageReadabilityRule:
    code = "R-PASS-004"
    severity = Severity.SHOULD

    def evaluate(self, context: PassageRuleContext) -> RuleResult:
        grade = flesch_kincaid_grade(context.body)
        low, high = fk_grade_range(context.target_band)
        passed = low <= grade <= high
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                f"Flesch-Kincaid grade {grade:.1f} within {low:.1f}–{high:.1f}"
                if passed
                else f"Flesch-Kincaid grade {grade:.1f} outside {low:.1f}–{high:.1f}"
            ),
            detail={
                "flesch_kincaid_grade": grade,
                "target_band": context.target_band,
                "expected_min": low,
                "expected_max": high,
            },
        )
