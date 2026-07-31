"""R-PASS-006 — sentence-length variance above a floor."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.common.text import sentence_length_variance
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.context import PassageRuleContext
from app.modules.ielts.reading.thresholds import MIN_SENTENCE_LENGTH_VARIANCE


class PassageSentenceVarianceRule:
    code = "R-PASS-006"
    severity = Severity.SHOULD

    def evaluate(self, context: PassageRuleContext) -> RuleResult:
        variance = sentence_length_variance(context.body)
        passed = variance >= MIN_SENTENCE_LENGTH_VARIANCE
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                f"Sentence-length variance {variance:.1f} meets floor "
                f"{MIN_SENTENCE_LENGTH_VARIANCE:.1f}"
                if passed
                else (
                    f"Sentence-length variance {variance:.1f} below floor "
                    f"{MIN_SENTENCE_LENGTH_VARIANCE:.1f}"
                )
            ),
            detail={
                "variance": variance,
                "min_variance": MIN_SENTENCE_LENGTH_VARIANCE,
            },
        )
