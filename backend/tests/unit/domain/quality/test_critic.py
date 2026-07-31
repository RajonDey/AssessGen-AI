"""Unit tests for critic output models."""

from app.domain.enums import FindingCategory, Severity
from app.domain.quality.critic import CriticFinding, CriticOutput


def test_critic_output_has_no_score_and_detects_blocking_findings() -> None:
    output = CriticOutput(
        findings=[
            CriticFinding(
                category=FindingCategory.AMBIGUITY,
                target="item:1",
                severity=Severity.SHOULD,
                explanation="Stem allows two readings.",
            ),
            CriticFinding(
                category=FindingCategory.ANSWER_NOT_SUPPORTED,
                target="item:2",
                severity=Severity.MUST,
                explanation="Answer not in passage.",
            ),
        ]
    )
    assert not hasattr(output, "overall_score")
    assert output.has_blocking_findings
    assert len(output.blocking_findings) == 1


def test_empty_critic_output_passes() -> None:
    output = CriticOutput()
    assert not output.has_blocking_findings
