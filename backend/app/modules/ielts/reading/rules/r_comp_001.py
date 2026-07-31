"""R-COMP-001 — answer is a verbatim substring of the passage."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import exact_key, find_verbatim_match, is_completion_type
from app.modules.ielts.reading.item_context import ItemRuleContext


class CompletionVerbatimAnswerRule:
    code = "R-COMP-001"
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
        if key is None or not key.values:
            return RuleResult(
                rule_code=self.code,
                passed=False,
                severity=self.severity,
                message="Missing exact answer key",
                detail={},
            )

        answer = key.values[0]
        match = find_verbatim_match(context.body, answer, case_sensitive=key.case_sensitive)
        passed = match is not None
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Answer appears verbatim in passage"
            if passed
            else "Answer not found verbatim in passage",
            detail={"answer": answer, "match": match or {}},
        )
