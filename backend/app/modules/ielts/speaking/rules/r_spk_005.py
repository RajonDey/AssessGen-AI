"""R-SPK-005 — Part 2 bullets are independent and non-redundant."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.speaking.context import SpeakingRuleContext


def _normalize_bullet(text: str) -> str:
    return " ".join(text.lower().split())


class SpeakingPart2BulletIndependenceRule:
    code = "R-SPK-005"
    severity = Severity.MUST

    def evaluate(self, context: SpeakingRuleContext) -> RuleResult:
        bullets = [_normalize_bullet(bullet) for bullet in context.part2.bullets]
        redundant_pairs: list[tuple[str, str]] = []
        for index, left in enumerate(bullets):
            for right in bullets[index + 1 :]:
                if left == right or left in right or right in left:
                    redundant_pairs.append((left, right))
        passed = not redundant_pairs
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Part 2 bullets are independent"
            if passed
            else "Part 2 bullets overlap or repeat",
            detail={"redundant_pairs": redundant_pairs[:3]},
        )
