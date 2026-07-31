"""R-PASS-005 — vocabulary profile matches target CEFR proxy."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.common.cefr import rare_word_ratio
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.bands import rare_word_ratio_max
from app.modules.ielts.reading.context import PassageRuleContext
from app.modules.ielts.reading.thresholds import RARE_ZIPF_THRESHOLD


class PassageVocabularyProfileRule:
    code = "R-PASS-005"
    severity = Severity.SHOULD

    def evaluate(self, context: PassageRuleContext) -> RuleResult:
        ratio = rare_word_ratio(context.body, zipf_threshold=RARE_ZIPF_THRESHOLD)
        max_ratio = rare_word_ratio_max(context.target_band)
        passed = ratio <= max_ratio
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                f"Rare-word ratio {ratio:.2%} within band limit {max_ratio:.2%}"
                if passed
                else f"Rare-word ratio {ratio:.2%} exceeds band limit {max_ratio:.2%}"
            ),
            detail={
                "rare_word_ratio": ratio,
                "max_ratio": max_ratio,
                "target_band": context.target_band,
                "zipf_threshold": RARE_ZIPF_THRESHOLD,
            },
        )
