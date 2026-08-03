"""R-WRIT-003 — word-count instruction present and correct for Task 2."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.writing.context import PromptRuleContext
from app.modules.ielts.writing.spec import WritingSpec

_MIN_WORDS_PATTERN = re.compile(r"\b(at least )?250\b", re.I)


class WritingWordCountInstructionRule:
    code = "R-WRIT-003"
    severity = Severity.MUST

    def evaluate(self, context: PromptRuleContext) -> RuleResult:
        if context.task != 2:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Word-count check skipped for non-Task-2 content",
                detail={"skipped": True},
            )
        bounds = WritingSpec()
        instruction = context.prompt.word_count_instruction
        combined = f"{context.text}\n{instruction}"
        has_minimum = _MIN_WORDS_PATTERN.search(combined) is not None
        mentions_words = re.search(r"\bwords?\b", combined, re.I) is not None
        passed = has_minimum and mentions_words and bounds.task2_min_words == 250
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Task 2 word-count instruction present"
            if passed
            else "Missing or incorrect Task 2 word-count instruction (≥250 words)",
            detail={"instruction": instruction},
        )
