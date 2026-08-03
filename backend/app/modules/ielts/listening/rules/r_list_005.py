"""R-LIST-005 — answer evidence spread across the transcript timeline."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.item_context import ItemRuleContext
from app.modules.ielts.reading.schemas import ReadingItem


class ListeningAnswerSpreadRule:
    code = "R-LIST-005"
    severity = Severity.MUST

    def evaluate_items(
        self,
        *,
        transcript: str,
        items: tuple[ReadingItem, ...],
    ) -> RuleResult:
        if len(items) < 2:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Not enough items to check spread",
                detail={"skipped": True},
            )
        body_len = max(len(transcript), 1)
        positions: list[float] = []
        for item in items:
            if item.evidence is None:
                continue
            positions.append(item.evidence.start / body_len)
        if len(positions) < 2:
            return RuleResult(
                rule_code=self.code,
                passed=True,
                severity=self.severity,
                message="Not enough evidence spans to check spread",
                detail={"skipped": True},
            )
        positions.sort()
        gap = positions[-1] - positions[0]
        passed = gap >= 0.15
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Answer evidence spread across transcript"
            if passed
            else "Answer evidence clustered in one part of the transcript",
            detail={"positions": positions, "gap_ratio": gap},
        )

    def evaluate(self, context: ItemRuleContext) -> RuleResult:
        del context
        msg = "R-LIST-005 is evaluated at set level via evaluate_items()"
        raise NotImplementedError(msg)
