"""R-WRIT-006 — GT Task 1 letter structure (N/A for Task 2 in Phase 1C)."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.writing.context import PromptRuleContext

_BULLET_MARKERS = re.compile(r"(^|\n)\s*[-•]\s+", re.M)


class WritingGtTask1LetterRule:
    code = "R-WRIT-006"
    severity = Severity.MUST

    def evaluate(self, context: PromptRuleContext) -> RuleResult:
        if context.task != 1:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="GT Task 1 letter check not applicable",
                detail={"skipped": True, "task": context.task},
            )
        text = context.text
        bullets = _BULLET_MARKERS.findall(text)
        has_recipient = re.search(r"\b(dear|write a letter to|recipient)\b", text, re.I) is not None
        passed = len(bullets) == 3 and has_recipient
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="GT Task 1 letter structure present"
            if passed
            else "GT Task 1 letter missing recipient or three bullet points",
            detail={"bullet_count": len(bullets), "has_recipient": has_recipient},
        )
