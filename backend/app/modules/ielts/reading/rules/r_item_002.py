"""R-ITEM-002 — stem does not leak the answer verbatim."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import (
    is_completion_type,
    primary_answer,
    stem_contains_answer,
)
from app.modules.ielts.reading.item_context import ItemRuleContext


class ItemNoAnswerLeakageRule:
    code = "R-ITEM-002"
    severity = Severity.MUST

    def evaluate(self, context: ItemRuleContext) -> RuleResult:
        if not is_completion_type(context.item.item_type):
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Not applicable to this item type",
                detail={"skipped": True},
            )
        answer = primary_answer(context.item)
        if answer is None:
            return RuleResult(
                rule_code=self.code,
                passed=False,
                severity=self.severity,
                message="No primary answer to check for leakage",
                detail={},
            )
        leaked = stem_contains_answer(context.item.stem, answer)
        return RuleResult(
            rule_code=self.code,
            passed=not leaked,
            severity=self.severity,
            message="Stem does not contain the answer"
            if not leaked
            else "Stem contains answer verbatim",
            detail={"answer": answer, "leaked": leaked},
        )
