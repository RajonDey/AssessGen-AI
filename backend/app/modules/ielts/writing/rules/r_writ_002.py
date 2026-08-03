"""R-WRIT-002 — question type is answerable as phrased."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.writing.context import PromptRuleContext

_TYPE_PATTERNS: dict[str, re.Pattern[str]] = {
    "opinion": re.compile(
        r"\b(to what extent|do you agree|disagree|in your opinion)\b",
        re.I,
    ),
    "discussion": re.compile(
        r"\b("
        r"discuss both|both views|some people|others believe|others argue|"
        r"on the one hand|while others"
        r")\b",
        re.I,
    ),
    "problem_solution": re.compile(
        r"\b(causes?|solutions?|problems?|what can be done|how can)\b",
        re.I,
    ),
    "advantages_disadvantages": re.compile(
        r"\b(advantages?|disadvantages?|outweigh|benefits?|drawbacks?)\b",
        re.I,
    ),
    "two_part": re.compile(r"\?", re.I),
}


class WritingQuestionTypeRule:
    code = "R-WRIT-002"
    severity = Severity.MUST

    def evaluate(self, context: PromptRuleContext) -> RuleResult:
        if context.task != 2:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Question-type check applies to Task 2 only",
                detail={"skipped": True},
            )
        pattern = _TYPE_PATTERNS.get(context.question_type)
        if pattern is None:
            return RuleResult(
                rule_code=self.code,
                passed=False,
                severity=self.severity,
                message=f"Unknown question type: {context.question_type}",
                detail={},
            )
        text = context.text
        if context.question_type == "two_part":
            question_words = len(re.findall(r"\bwhat\b|\bwhy\b|\bhow\b", text, re.I))
            passed = text.count("?") >= 2 or question_words >= 2
        else:
            passed = pattern.search(text) is not None
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Prompt matches declared question type"
            if passed
            else f"Prompt does not match question type '{context.question_type}'",
            detail={"question_type": context.question_type},
        )
