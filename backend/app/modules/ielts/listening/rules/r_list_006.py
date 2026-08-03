"""R-LIST-006 — self-correction distractor pattern."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.listening.context import ScriptRuleContext

_SELF_CORRECTION = re.compile(
    r"(sorry,?\s+i mean|no,?\s+i mean|—\s*no,|actually,?\s+i|wait,?\s+)",
    re.I,
)


class ListeningSelfCorrectionRule:
    code = "R-LIST-006"
    severity = Severity.SHOULD

    def evaluate(self, context: ScriptRuleContext) -> RuleResult:
        if context.section != 1:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Self-correction check optional outside Section 1",
                detail={"skipped": True},
            )
        passed = _SELF_CORRECTION.search(context.transcript) is not None
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                "Self-correction distractor present"
                if passed
                else "No self-correction pattern"
            ),
            detail={},
        )
