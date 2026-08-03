"""Deterministic L1 quality evaluation for IELTS Writing graph nodes."""

from __future__ import annotations

from app.domain.quality.report import QualityReport
from app.modules.ielts.writing.context import PromptRuleContext
from app.modules.ielts.writing.rules import build_prompt_rule_registry
from app.modules.ielts.writing.schemas import WritingTask2Prompt
from app.workflows.nodes.reading_quality import quality_failure_message, report_to_state


def evaluate_prompt_quality(
    prompt: WritingTask2Prompt,
    *,
    target_band: float,
) -> QualityReport:
    registry = build_prompt_rule_registry()
    context = PromptRuleContext(prompt=prompt, target_band=target_band)
    return registry.run_all(context)


__all__ = [
    "evaluate_prompt_quality",
    "quality_failure_message",
    "report_to_state",
]
