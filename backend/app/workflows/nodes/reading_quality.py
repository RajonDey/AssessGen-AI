"""Deterministic L1 quality evaluation for IELTS Reading graph nodes."""

from __future__ import annotations

from app.domain.quality.protocol import RuleResult
from app.domain.quality.report import QualityReport
from app.modules.ielts.reading.agent_schemas import PassagePlan
from app.modules.ielts.reading.context import PassageRuleContext
from app.modules.ielts.reading.item_context import ItemRuleContext
from app.modules.ielts.reading.rules import (
    build_item_rule_registry,
    build_passage_rule_registry,
    build_set_rule_registry,
)
from app.modules.ielts.reading.schemas import ReadingItem, ReadingPassage
from app.modules.ielts.reading.set_context import SetRuleContext
from app.modules.ielts.reading.spec import AcademicReadingSpec


def evaluate_passage_quality(
    passage: ReadingPassage,
    plan: PassagePlan,
    *,
    target_band: float,
    spec: AcademicReadingSpec | None = None,
) -> QualityReport:
    bounds = spec or AcademicReadingSpec()
    registry = build_passage_rule_registry()
    planned_types = tuple(block.item_type.value for block in plan.question_blocks)
    context = PassageRuleContext(
        passage=passage,
        target_band=target_band,
        planned_item_types=planned_types,
        word_count_min=bounds.passage_word_count_min,
        word_count_max=bounds.passage_word_count_max,
    )
    return registry.run_all(context)


def evaluate_items_quality(
    passage: ReadingPassage,
    items: tuple[ReadingItem, ...],
    plan: PassagePlan,
) -> QualityReport:
    item_registry = build_item_rule_registry()
    results: list[RuleResult] = []
    for index, item in enumerate(items):
        context = ItemRuleContext(
            passage=passage,
            item=item,
            item_index=index,
            all_items=items,
        )
        report = item_registry.run_all(context)
        results.extend(report.results)

    type_counts = {block.item_type.value: block.count for block in plan.question_blocks}
    set_context = SetRuleContext(
        passage=passage,
        items=items,
        expected_item_count=sum(type_counts.values()),
        planned_type_counts=type_counts,
    )
    set_report = build_set_rule_registry().run_all(set_context)
    results.extend(set_report.results)
    return QualityReport(results=tuple(results))


def report_to_state(report: QualityReport) -> dict[str, object]:
    return {
        "passed": report.passed,
        "has_blocking_failures": report.has_blocking_failures,
        "must_failure_count": len(report.must_failures),
        "results": [result.model_dump(mode="json") for result in report.results],
    }


def quality_failure_message(scope: str, report: QualityReport) -> str:
    if not report.must_failures:
        return f"{scope} quality gate failed"
    details = "; ".join(
        f"{result.rule_code}: {result.message}" for result in report.must_failures[:3]
    )
    return f"{scope} quality gate failed — {details}"
