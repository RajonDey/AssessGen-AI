"""R-COMP-006 — answer is not a bare function word."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import FUNCTION_WORDS, exact_key, is_completion_type
from app.modules.ielts.reading.item_context import ItemRuleContext


class CompletionNotFunctionWordRule:
    code = "R-COMP-006"
    severity = Severity.SHOULD

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
        if key is None or not key.values:
            return RuleResult(
                rule_code=self.code,
                passed=False,
                severity=self.severity,
                message="Missing answer",
                detail={},
            )

        answer = key.values[0].strip().lower()
        passed = answer not in FUNCTION_WORDS
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Answer is not a function word" if passed else "Answer is a function word",
            detail={"answer": key.values[0]},
        )
