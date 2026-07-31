"""R-COMP-004 — accepted alternates also appear verbatim in the passage."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import exact_key, find_verbatim_match, is_completion_type
from app.modules.ielts.reading.item_context import ItemRuleContext


class CompletionAlternateAnswersRule:
    code = "R-COMP-004"
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
        if key is None or not key.accept:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="No alternate answers to validate",
                detail={"skipped": True},
            )

        missing: list[str] = []
        for alternate in key.accept:
            if (
                find_verbatim_match(context.body, alternate, case_sensitive=key.case_sensitive)
                is None
            ):
                missing.append(alternate)

        passed = not missing
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="All alternates appear verbatim"
            if passed
            else "Some alternates not verbatim in passage",
            detail={"missing": missing},
        )
