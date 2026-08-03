"""Deterministic L1 quality evaluation for IELTS Speaking graph nodes."""

from __future__ import annotations

from app.domain.quality.report import QualityReport
from app.modules.ielts.speaking.context import SpeakingRuleContext
from app.modules.ielts.speaking.rules import build_speaking_rule_registry
from app.modules.ielts.speaking.schemas import SpeakingPart1And2
from app.workflows.nodes.reading_quality import quality_failure_message, report_to_state


def evaluate_speaking_quality(
    content: SpeakingPart1And2,
    *,
    target_band: float,
) -> QualityReport:
    registry = build_speaking_rule_registry()
    context = SpeakingRuleContext(content=content, target_band=target_band)
    return registry.run_all(context)


__all__ = [
    "evaluate_speaking_quality",
    "quality_failure_message",
    "report_to_state",
]
