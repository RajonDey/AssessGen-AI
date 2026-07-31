"""R-COMP-002 — answer word count obeys the stated limit."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import (
    count_answer_words,
    exact_key,
    is_completion_type,
    parse_word_limit,
)
from app.modules.ielts.reading.item_context import ItemRuleContext


class CompletionWordLimitRule:
    code = "R-COMP-002"
    severity = Severity.MUST

    def evaluate(self, context: ItemRuleContext) -> RuleResult:
        if not is_completion_type(context.item.item_type):
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Not a completion item",
                detail={"skipped": True},
            )

        key = exact_key(context.item)
        limit = parse_word_limit(context.item.instructions)
        if key is None or not key.values or limit is None:
            return RuleResult(
                rule_code=self.code,
                passed=False,
                severity=self.severity,
                message="Cannot validate word limit without answer and instructions",
                detail={},
            )

        answer = key.values[0]
        words = count_answer_words(answer)
        passed = words <= limit
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                f"Answer uses {words} word(s), within limit {limit}"
                if passed
                else f"Answer uses {words} word(s), exceeds limit {limit}"
            ),
            detail={"word_count": words, "limit": limit, "answer": answer},
        )
