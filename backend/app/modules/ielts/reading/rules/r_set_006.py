"""R-SET-006 — no two items test the same fact."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.helpers import primary_answer
from app.modules.ielts.reading.set_context import SetRuleContext


class SetNoDuplicateFactRule:
    code = "R-SET-006"
    severity = Severity.MUST

    def evaluate(self, context: SetRuleContext) -> RuleResult:
        seen_answers: dict[str, int] = {}
        seen_quotes: dict[str, int] = {}
        duplicates: list[dict[str, str | int]] = []

        for index, item in enumerate(context.items):
            answer = primary_answer(item)
            if answer is not None:
                key = answer.strip().lower()
                if key in seen_answers:
                    duplicates.append(
                        {
                            "kind": "answer",
                            "value": answer,
                            "indices": f"{seen_answers[key]},{index}",
                        }
                    )
                else:
                    seen_answers[key] = index

            if item.evidence is not None:
                quote_key = item.evidence.quote.strip().lower()
                if quote_key in seen_quotes:
                    duplicates.append(
                        {
                            "kind": "evidence",
                            "value": item.evidence.quote[:80],
                            "indices": f"{seen_quotes[quote_key]},{index}",
                        }
                    )
                else:
                    seen_quotes[quote_key] = index

        passed = not duplicates
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Items test distinct facts"
            if passed
            else "Duplicate fact detected across items",
            detail={"duplicates": duplicates},
        )
