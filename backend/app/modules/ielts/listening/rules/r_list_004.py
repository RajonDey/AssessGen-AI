"""R-LIST-004 — speaker labels consistent with declared speakers."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.listening.context import ScriptRuleContext
from app.modules.ielts.listening.helpers import speaker_ids


class ListeningSpeakerLabelRule:
    code = "R-LIST-004"
    severity = Severity.MUST

    def evaluate(self, context: ScriptRuleContext) -> RuleResult:
        allowed = speaker_ids(context.script)
        unknown = sorted(
            {turn.speaker for turn in context.script.turns if turn.speaker not in allowed}
        )
        passed = not unknown and len(context.script.turns) >= 1
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Speaker labels match declared speakers"
            if passed
            else f"Unknown speaker labels: {unknown}",
            detail={"unknown_speakers": unknown, "declared": sorted(allowed)},
        )
