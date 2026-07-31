"""Revision loop helpers — convert rule/critic outcomes into reviser input."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.critic import CriticFinding, CriticOutput
from app.domain.quality.protocol import RuleResult
from app.domain.quality.report import QualityReport
from app.modules.ielts.reading.agent_schemas import RevisionFinding


def rule_failures_to_findings(report: QualityReport) -> tuple[RevisionFinding, ...]:
    return tuple(
        RevisionFinding(
            source="rule",
            target=str(result.detail.get("target", result.rule_code)),
            severity=result.severity,
            message=result.message,
            suggested_fix=(
                str(result.detail["suggested_fix"]) if result.detail.get("suggested_fix") else None
            ),
        )
        for result in report.must_failures
    )


def critic_findings_to_revision(findings: tuple[CriticFinding, ...]) -> tuple[RevisionFinding, ...]:
    return tuple(
        RevisionFinding(
            source="critic",
            target=finding.target,
            severity=finding.severity,
            message=finding.explanation,
            suggested_fix=finding.suggested_fix,
        )
        for finding in findings
        if finding.severity == Severity.MUST
    )


def quality_report_from_state(payload: dict[str, object]) -> QualityReport:
    raw_results = payload.get("results", [])
    results = tuple(RuleResult.model_validate(item) for item in raw_results)  # type: ignore[arg-type]
    return QualityReport(results=results)


def critic_output_from_state(payload: dict[str, object] | None) -> CriticOutput:
    if not payload:
        return CriticOutput()
    return CriticOutput.model_validate(payload)
