"""R-SPK-001 — Part 2 cue card has exactly three bullets."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.speaking.context import SpeakingRuleContext
from app.modules.ielts.speaking.spec import SpeakingSpec


class SpeakingPart2BulletCountRule:
    code = "R-SPK-001"
    severity = Severity.MUST

    def evaluate(self, context: SpeakingRuleContext) -> RuleResult:
        expected = SpeakingSpec().part2_bullet_count
        count = len(context.part2.bullets)
        passed = count == expected
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message=f"Part 2 has {expected} cue-card bullets"
            if passed
            else f"Part 2 has {count} bullets (expected {expected})",
            detail={"bullet_count": count, "expected": expected},
        )
