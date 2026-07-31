"""R-ITEM-006 — no near-duplicate stem within the set."""

from __future__ import annotations

from rapidfuzz import fuzz

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.item_context import ItemRuleContext

DUPLICATE_THRESHOLD = 90


class ItemNoDuplicateStemRule:
    code = "R-ITEM-006"
    severity = Severity.SHOULD

    def evaluate(self, context: ItemRuleContext) -> RuleResult:
        stem = context.item.stem.strip()
        duplicates: list[dict[str, int | str]] = []
        for index, other in enumerate(context.all_items):
            if index == context.item_index:
                continue
            score = fuzz.ratio(stem, other.stem.strip())
            if score >= DUPLICATE_THRESHOLD:
                duplicates.append({"index": index, "score": score, "stem": other.stem[:80]})

        passed = not duplicates
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Stem is distinct within the set" if passed else "Near-duplicate stem detected",
            detail={"duplicates": duplicates, "threshold": DUPLICATE_THRESHOLD},
        )
