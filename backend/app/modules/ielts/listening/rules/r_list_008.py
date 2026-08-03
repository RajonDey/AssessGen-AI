"""R-LIST-008 — numbers and dates in natural spoken form."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.listening.context import ScriptRuleContext

_RAW_LONG_DIGITS = re.compile(r"\b\d{5,}\b")


class ListeningSpokenNumbersRule:
    code = "R-LIST-008"
    severity = Severity.MUST

    def evaluate(self, context: ScriptRuleContext) -> RuleResult:
        matches = _RAW_LONG_DIGITS.findall(context.transcript)
        passed = not matches
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="No raw long digit sequences"
            if passed
            else f"Raw digit sequences found: {matches[:3]}",
            detail={"matches": matches[:5]},
        )
