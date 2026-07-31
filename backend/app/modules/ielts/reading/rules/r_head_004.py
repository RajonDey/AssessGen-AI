"""R-HEAD-004 — headings read as noun phrases, not full sentences."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import is_heading_match
from app.modules.ielts.reading.item_context import ItemRuleContext

VERB_PATTERN = re.compile(
    r"\b(is|are|was|were|has|have|had|will|can|should|could)\b", re.IGNORECASE
)
MAX_HEADING_WORDS = 12


class HeadingNounPhraseRule:
    code = "R-HEAD-004"
    severity = Severity.SHOULD

    def evaluate(self, context: ItemRuleContext) -> RuleResult:
        if not is_heading_match(context.item.item_type):
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Not a heading match item",
                detail={"skipped": True},
            )

        offenders: list[dict[str, str | int | bool]] = []
        for heading in context.item.options:
            text = heading.strip()
            words = text.split()
            offenders.append(
                {
                    "heading": text[:80],
                    "too_long": len(words) > MAX_HEADING_WORDS,
                    "has_verb": bool(VERB_PATTERN.search(text)),
                    "ends_sentence": text.endswith("."),
                }
            )

        passed = all(
            not row["too_long"] and not row["has_verb"] and not row["ends_sentence"]
            for row in offenders
        )
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Headings look like noun phrases"
            if passed
            else "Some headings look like sentences",
            detail={"headings": offenders},
        )
