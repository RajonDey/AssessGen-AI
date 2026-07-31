"""R-PASS-007 — no first/second-person address in Academic passages."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.common.text import find_person_pronouns
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.context import PassageRuleContext

_PERSON_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\byou\b"),
    re.compile(r"\byour\b"),
    re.compile(r"\bwe\b"),
    re.compile(r"\bour\b"),
    re.compile(r"\bus\b"),
    re.compile(r"\bi\b"),
    re.compile(r"\bmy\b"),
)


class PassageNoSecondPersonRule:
    code = "R-PASS-007"
    severity = Severity.MUST

    def evaluate(self, context: PassageRuleContext) -> RuleResult:
        hits = find_person_pronouns(context.body, _PERSON_PATTERNS)
        passed = not hits
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                "No first/second-person address detected"
                if passed
                else "First/second-person address detected"
            ),
            detail={"patterns_matched": hits},
        )
