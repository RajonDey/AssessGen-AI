"""R-SPK-004 — Part 3 question count (N/A in Phase 1C)."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.speaking.context import SpeakingRuleContext


class SpeakingPart3CountRule:
    code = "R-SPK-004"
    severity = Severity.MUST

    def evaluate(self, context: SpeakingRuleContext) -> RuleResult:
        del context
        return RuleResult(
            rule_code=self.code,
            passed=True,
            severity=self.severity,
            message="Part 3 not generated in Phase 1C",
            detail={"skipped": True},
        )
