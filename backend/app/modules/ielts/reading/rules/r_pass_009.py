"""R-PASS-009 — no factual self-contradiction between stated figures."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.common.text import find_contradictory_subject_values
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.context import PassageRuleContext


class PassageNoContradictionRule:
    code = "R-PASS-009"
    severity = Severity.MUST

    def evaluate(self, context: PassageRuleContext) -> RuleResult:
        contradictions = find_contradictory_subject_values(context.body)
        passed = not contradictions
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                "No contradictory subject/value claims detected"
                if passed
                else "Contradictory subject/value claims detected"
            ),
            detail={"contradictions": contradictions},
        )
