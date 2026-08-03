"""R-LIST-001 — answers spoken exactly as they must be written (verbatim in transcript)."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import exact_key, find_verbatim_match, is_completion_type
from app.modules.ielts.reading.item_context import ItemRuleContext


class ListeningVerbatimAnswerRule:
    code = "R-LIST-001"
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
            message="Answer appears verbatim in transcript"
            if passed
            else "Answer not found verbatim in transcript",
            detail={"answer": answer, "match": match or {}},
        )
