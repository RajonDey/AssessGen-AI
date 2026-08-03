"""R-LIST-007 — spellable proper nouns spelled out when needed."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.listening.context import ScriptRuleContext

_SPELL_OUT = re.compile(r"\b([A-Z]-){2,}[A-Z]\b")
_CAPITALIZED_NAME = re.compile(r"\b[A-Z][a-z]{2,}\b")


class ListeningSpelledProperNounRule:
    code = "R-LIST-007"
    severity = Severity.SHOULD

    def evaluate(self, context: ScriptRuleContext) -> RuleResult:
        text = context.transcript
        names = _CAPITALIZED_NAME.findall(text)
        if not names:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="No capitalized proper nouns to check",
                detail={"skipped": True},
            )
        passed = _SPELL_OUT.search(text) is not None
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                "Spelled-out proper noun present"
                if passed
                else "Proper nouns without spell-out"
            ),
            detail={"sample_names": names[:5]},
        )
