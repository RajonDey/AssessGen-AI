"""R-COMP-005 — filling the gap produces a grammatical sentence."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import (
    GAP_PATTERN,
    exact_key,
    fill_gap,
    is_completion_type,
)
from app.modules.ielts.reading.item_context import ItemRuleContext


class CompletionGapGrammarRule:
    code = "R-COMP-005"
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

        stem = context.item.stem
        key = exact_key(context.item)
        if key is None or not key.values:
            return RuleResult(
                rule_code=self.code,
                passed=False,
                severity=self.severity,
                message="Missing answer for gap fill check",
                detail={},
            )

        if not GAP_PATTERN.search(stem):
            return RuleResult(
                rule_code=self.code,
                passed=False,
                severity=self.severity,
                message="Stem has no gap marker",
                detail={"stem": stem},
            )

        filled = fill_gap(stem, key.values[0]).strip()
        starts_capital = bool(filled) and filled[0].isupper()
        ends_punct = bool(re.search(r"[.!?]$", filled))
        no_double_space = "  " not in filled
        passed = starts_capital and ends_punct and no_double_space

        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Filled gap looks grammatical"
            if passed
            else "Filled gap fails basic grammar checks",
            detail={
                "filled": filled,
                "starts_capital": starts_capital,
                "ends_punct": ends_punct,
                "no_double_space": no_double_space,
            },
        )
