"""Deterministic L1 quality evaluation for IELTS Listening graph nodes."""

from __future__ import annotations

from app.domain.quality.protocol import RuleResult
from app.domain.quality.report import QualityReport
from app.modules.ielts.listening.context import ScriptRuleContext
from app.modules.ielts.listening.helpers import script_to_passage
from app.modules.ielts.listening.rules import (
    ANSWER_SPREAD_RULE,
    LISTENING_ITEM_RULES,
    build_script_rule_registry,
)
from app.modules.ielts.listening.schemas import ListeningScript
from app.modules.ielts.reading.agent_schemas import QuestionBlockPlan
from app.modules.ielts.reading.item_context import ItemRuleContext
from app.modules.ielts.reading.rules import build_item_rule_registry, build_set_rule_registry
from app.modules.ielts.reading.schemas import ReadingItem
from app.modules.ielts.reading.set_context import SetRuleContext
from app.workflows.nodes.reading_quality import quality_failure_message, report_to_state


def evaluate_script_quality(
    script: ListeningScript,
    *,
    target_band: float,
) -> QualityReport:
    registry = build_script_rule_registry()
    context = ScriptRuleContext(
        script=script,
        section=script.section,
        target_band=target_band,
    )
    return registry.run_all(context)


def evaluate_listening_items_quality(
    script: ListeningScript,
    items: tuple[ReadingItem, ...],
    question_blocks: tuple[QuestionBlockPlan, ...],
) -> QualityReport:
    passage = script_to_passage(script)
    transcript = script.transcript

    results: list[RuleResult] = []
    for rule in LISTENING_ITEM_RULES:
        for index, item in enumerate(items):
            context = ItemRuleContext(
                passage=passage,
                item=item,
                item_index=index,
                all_items=items,
            )
            results.append(rule.evaluate(context))

    reading_item_registry = build_item_rule_registry()
    for index, item in enumerate(items):
        context = ItemRuleContext(
            passage=passage,
            item=item,
            item_index=index,
            all_items=items,
        )
        report = reading_item_registry.run_all(context)
        results.extend(report.results)

    type_counts = {block.item_type.value: block.count for block in question_blocks}
    set_context = SetRuleContext(
        passage=passage,
        items=items,
        expected_item_count=sum(type_counts.values()),
        planned_type_counts=type_counts,
    )
    set_report = build_set_rule_registry().run_all(set_context)
    results.extend(set_report.results)
    results.append(ANSWER_SPREAD_RULE.evaluate_items(transcript=transcript, items=items))

    return QualityReport(results=tuple(results))


__all__ = [
    "evaluate_listening_items_quality",
    "evaluate_script_quality",
    "quality_failure_message",
    "report_to_state",
]
