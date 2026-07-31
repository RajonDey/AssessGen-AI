"""R-SET-005 — answers are spread across the passage, not clustered early."""

from __future__ import annotations

from collections import Counter

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import paragraph_label_order
from app.modules.ielts.reading.set_context import SetRuleContext

EARLY_PARAGRAPH_LIMIT = 2
CLUSTER_RATIO = 0.6


class SetAnswerSpreadRule:
    code = "R-SET-005"
    severity = Severity.SHOULD

    def evaluate(self, context: SetRuleContext) -> RuleResult:
        if context.paragraph_count < EARLY_PARAGRAPH_LIMIT + 1:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Passage too short for spread check",
                detail={"skipped": True},
            )

        counts = Counter(
            item.evidence.paragraph.upper() for item in context.items if item.evidence is not None
        )
        if not counts:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="No evidence spans to check spread",
                detail={"skipped": True},
            )

        early_labels = {
            p.label.upper()
            for p in context.passage.paragraphs
            if paragraph_label_order(p.label) < EARLY_PARAGRAPH_LIMIT
        }
        total = sum(counts.values())
        early = sum(counts[label] for label in early_labels if label in counts)
        ratio = early / total
        passed = ratio <= CLUSTER_RATIO
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=(
                f"{ratio:.0%} of answers in first {EARLY_PARAGRAPH_LIMIT} paragraphs"
                if passed
                else f"{ratio:.0%} of answers clustered in early paragraphs"
            ),
            detail={"counts": dict(counts), "early_ratio": ratio, "threshold": CLUSTER_RATIO},
        )
