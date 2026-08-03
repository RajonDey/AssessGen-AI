"""R-WRIT-001 — Task 2 prompt states a clear, arguable proposition."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.writing.context import PromptRuleContext

_PROPOSITION_MARKERS = re.compile(
    r"\b("
    r"to what extent|do you agree|discuss both|what are the causes|"
    r"advantages outweigh|disadvantages outweigh|in your opinion|"
    r"some people believe|others argue|why is this|what can be done"
    r")\b",
    re.I,
)


class WritingClearPropositionRule:
    code = "R-WRIT-001"
    severity = Severity.MUST

    def evaluate(self, context: PromptRuleContext) -> RuleResult:
        if context.task != 2:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Proposition check applies to Task 2 only",
                detail={"skipped": True},
            )
        text = context.text.strip()
        has_marker = _PROPOSITION_MARKERS.search(text) is not None
        has_question = "?" in text
        passed = len(text) >= 80 and (has_marker or has_question)
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Clear arguable proposition present"
            if passed
            else "Prompt lacks a clear arguable proposition",
            detail={"length": len(text), "has_marker": has_marker, "has_question": has_question},
        )
