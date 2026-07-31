"""R-COMP-003 — stated limit uses legal IELTS phrasing."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import instructions_are_legal, is_completion_type
from app.modules.ielts.reading.item_context import ItemRuleContext


class CompletionLegalPhrasingRule:
    code = "R-COMP-003"
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

        instructions = context.item.instructions
        passed = instructions_are_legal(instructions)
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Instructions use legal IELTS phrasing"
            if passed
            else "Illegal instruction phrasing",
            detail={"instructions": instructions},
        )
