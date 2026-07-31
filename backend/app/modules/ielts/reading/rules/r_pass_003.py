"""R-PASS-003 — no placeholder or meta text."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.context import PassageRuleContext

_BANNED_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bas an ai\b", re.IGNORECASE), "as an AI"),
    (re.compile(r"^\s*passage\s*:", re.IGNORECASE | re.MULTILINE), "Passage:"),
    (re.compile(r"\[insert[^\]]*\]", re.IGNORECASE), "[insert…]"),
    (re.compile(r"in this (passage|essay) (we|i) will", re.IGNORECASE), "meta preamble"),
)


class PassageNoMetaTextRule:
    code = "R-PASS-003"
    severity = Severity.MUST

    def evaluate(self, context: PassageRuleContext) -> RuleResult:
        body = context.body
        matches: list[str] = []
        for pattern, label in _BANNED_PATTERNS:
            if pattern.search(body):
                matches.append(label)
        passed = not matches
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                "No placeholder or meta text detected"
                if passed
                else f"Placeholder or meta text detected: {', '.join(matches)}"
            ),
            detail={"matches": matches},
        )
