"""R-SPK-002 — Part 2 ends with an 'and explain…' prompt."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.speaking.context import SpeakingRuleContext

_EXPLAIN_PROMPT = re.compile(r"\band explain\b", re.I)


class SpeakingPart2ExplainPromptRule:
    code = "R-SPK-002"
    severity = Severity.MUST

    def evaluate(self, context: SpeakingRuleContext) -> RuleResult:
        prompt = context.part2.explain_prompt.strip()
        passed = _EXPLAIN_PROMPT.search(prompt) is not None
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Part 2 includes 'and explain…' prompt"
            if passed
            else "Part 2 missing 'and explain…' closing prompt",
            detail={"explain_prompt": prompt},
        )
