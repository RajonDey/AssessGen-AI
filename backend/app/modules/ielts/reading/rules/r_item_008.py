"""R-ITEM-008 — instructions match item type (word limit iff completion)."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import (
    instructions_are_legal,
    is_completion_type,
    is_heading_match,
)
from app.modules.ielts.reading.item_context import ItemRuleContext


class ItemInstructionsMatchTypeRule:
    code = "R-ITEM-008"
    severity = Severity.MUST

    def evaluate(self, context: ItemRuleContext) -> RuleResult:
        instructions = context.item.instructions
        item_type = context.item.item_type

        if is_completion_type(item_type):
            passed = instructions is not None and instructions_are_legal(instructions)
            return RuleResult(
                rule_code=self.code,
                passed=passed,
                severity=self.severity,
                message=(
                    "Completion item has legal word-limit instructions"
                    if passed
                    else "Completion item requires legal IELTS word-limit instructions"
                ),
                detail={"instructions": instructions},
            )

        if is_heading_match(item_type):
            passed = instructions is None or not instructions.strip()
            return RuleResult(
                rule_code=self.code,
                passed=passed,
                severity=self.severity,
                message="Heading match has no word-limit instructions"
                if passed
                else "Unexpected instructions",
                detail={"instructions": instructions},
            )

        return RuleResult(
            rule_code=self.code,
            passed=True,
            severity=self.severity,
            message="Not applicable",
            detail={"skipped": True},
        )
