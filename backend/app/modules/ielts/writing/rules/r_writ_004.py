"""R-WRIT-004 — culturally neutral and globally accessible topic."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.writing.context import PromptRuleContext

_LOCALISED_ONLY = re.compile(
    r"\b("
    r"your country's|our nation's|the uk only|american citizens only|"
    r"brexit referendum|us electoral college|a-level exams|sat scores"
    r")\b",
    re.I,
)


class WritingCulturalNeutralityRule:
    code = "R-WRIT-004"
    severity = Severity.SHOULD

    def evaluate(self, context: PromptRuleContext) -> RuleResult:
        match = _LOCALISED_ONLY.search(context.text)
        passed = match is None
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Topic appears culturally neutral"
            if passed
            else "Topic may assume culture-specific knowledge",
            detail={"match": match.group(0) if match else None},
        )
