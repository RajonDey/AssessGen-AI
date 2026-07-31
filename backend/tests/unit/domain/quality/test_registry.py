"""Rule registry tests."""

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.domain.quality.registry import RuleRegistry


class _AlwaysPassRule:
    code = "R-TEST-001"
    severity = Severity.MUST

    def evaluate(self, context: object) -> RuleResult:
        del context
        return RuleResult(
            rule_code=self.code,
            passed=True,
            severity=self.severity,
            message="ok",
        )


class _MustFailRule:
    code = "R-TEST-002"
    severity = Severity.MUST

    def evaluate(self, context: object) -> RuleResult:
        del context
        return RuleResult(
            rule_code=self.code,
            passed=False,
            severity=self.severity,
            message="blocked",
        )


def test_registry_runs_rules_in_stable_code_order() -> None:
    registry = RuleRegistry()
    registry.register(_MustFailRule())
    registry.register(_AlwaysPassRule())
    report = registry.run_all(object())
    assert [r.rule_code for r in report.results] == ["R-TEST-001", "R-TEST-002"]


def test_registry_blocks_on_must_failure() -> None:
    registry = RuleRegistry()
    registry.register(_MustFailRule())
    report = registry.run_all(object())
    assert not report.passed
    assert report.has_blocking_failures
    assert len(report.must_failures) == 1
