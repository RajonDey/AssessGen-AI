"""R-WRIT-005 — topic does not require specialist knowledge."""

from __future__ import annotations

import re

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.writing.context import PromptRuleContext

_SPECIALIST_TERMS = re.compile(
    r"\b("
    r"quantum|epigenetic|macroeconomic|jurisprudence|isomer|"
    r"mitochondrial|stochastic|homologous|pathophysiology"
    r")\b",
    re.I,
)


class WritingNoSpecialistKnowledgeRule:
    code = "R-WRIT-005"
    severity = Severity.SHOULD

    def evaluate(self, context: PromptRuleContext) -> RuleResult:
        match = _SPECIALIST_TERMS.search(context.text)
        passed = match is None
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Topic avoids specialist terminology"
            if passed
            else "Topic may require specialist knowledge",
            detail={"match": match.group(0) if match else None},
        )
