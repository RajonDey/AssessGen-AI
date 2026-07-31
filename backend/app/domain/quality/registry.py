"""Rule discovery and execution."""

from __future__ import annotations

from typing import Any

from app.domain.quality.protocol import Rule, RuleResult
from app.domain.quality.report import QualityReport


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        if rule.code in self._rules:
            msg = f"Rule already registered: {rule.code}"
            raise ValueError(msg)
        self._rules[rule.code] = rule

    def get(self, code: str) -> Rule | None:
        return self._rules.get(code)

    def codes(self) -> tuple[str, ...]:
        return tuple(sorted(self._rules))

    def run_all(self, context: Any) -> QualityReport:
        results: list[RuleResult] = []
        for code in sorted(self._rules):
            results.append(self._rules[code].evaluate(context))
        return QualityReport(results=tuple(results))

    def run_codes(self, context: Any, codes: tuple[str, ...]) -> QualityReport:
        results: list[RuleResult] = []
        for code in codes:
            rule = self._rules.get(code)
            if rule is None:
                msg = f"Unknown rule code: {code}"
                raise KeyError(msg)
            results.append(rule.evaluate(context))
        return QualityReport(results=tuple(results))
