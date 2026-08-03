"""R-LIST-002 — natural spoken register, not written essay prose."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.listening.context import ScriptRuleContext

_SPOKEN_MARKERS = (
    re.compile(r"\b(i'm|you're|we're|they're|it's|don't|can't|won't|isn't)\b", re.I),
    re.compile(r"\?"),
    re.compile(r"^\s*(well|oh|so|right|okay|thanks)\b", re.I | re.M),
    re.compile(r"\b(let me|could you|would you|i'd like)\b", re.I),
)


class ListeningSpokenRegisterRule:
    code = "R-LIST-002"
    severity = Severity.MUST

    def evaluate(self, context: ScriptRuleContext) -> RuleResult:
        text = context.transcript
        hits = sum(1 for pattern in _SPOKEN_MARKERS if pattern.search(text))
        passed = hits >= 2
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                "Spoken register markers present"
                if passed
                else "Transcript reads too formal/written"
            ),
            detail={"marker_hits": hits, "required": 2},
        )
