"""R-LIST-003 — hesitations and false starts (Section 1 dialogue)."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.listening.context import ScriptRuleContext

_HESITATION = re.compile(r"\b(um|uh|er|hmm)\b|—|-\s|\.\.\.", re.I)


class ListeningHesitationRule:
    code = "R-LIST-003"
    severity = Severity.SHOULD

    def evaluate(self, context: ScriptRuleContext) -> RuleResult:
        if context.section != 1:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Hesitation check applies to Section 1 only",
                detail={"skipped": True},
            )
        passed = _HESITATION.search(context.transcript) is not None
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Hesitation markers present" if passed else "No hesitation/false-start markers",
            detail={},
        )
