"""Reading quality node helpers."""

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.domain.quality.report import QualityReport
from app.workflows.nodes.reading_quality import quality_failure_message


def test_quality_failure_message_lists_rules() -> None:
    report = QualityReport(
        results=(
            RuleResult(
                rule_code="R-PASS-001",
                passed=False,
                severity=Severity.MUST,
                message="Word count 612 is outside 700–1000",
                detail={},
            ),
        )
    )
    message = quality_failure_message("Passage", report)
    assert "R-PASS-001" in message
    assert "612" in message
