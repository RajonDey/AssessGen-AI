"""Planted-defect benchmark — deterministic ground truth without an examiner."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

from app.modules.ielts.reading.item_context import ItemRuleContext
from app.modules.ielts.listening.rules.r_list_001 import ListeningVerbatimAnswerRule
from app.modules.ielts.reading.rules.r_comp_001 import CompletionVerbatimAnswerRule
from app.modules.ielts.reading.rules.r_comp_002 import CompletionWordLimitRule
from app.modules.ielts.reading.schemas import ReadingItem, ReadingPassage
from harness.schema import TaskMetric, TaskResult

PLANTED_DEFECT_RULES: dict[str, object] = {
    "R-COMP-001": CompletionVerbatimAnswerRule(),
    "R-COMP-002": CompletionWordLimitRule(),
    "R-LIST-001": ListeningVerbatimAnswerRule(),
}


def _load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rules_for_fixture(payload: dict[str, Any]) -> list[tuple[str, object]]:
    codes = payload.get("rules_under_test") or payload.get("expected_rule_failures") or []
    rules: list[tuple[str, object]] = []
    for code in codes:
        rule = PLANTED_DEFECT_RULES.get(code)
        if rule is not None:
            rules.append((code, rule))
    if rules:
        return rules
    return list(PLANTED_DEFECT_RULES.items())


def run_planted_defect_task(
    *,
    fixture_path: Path,
    model_profile: str,
    mode: Literal["mock", "live"],
    task_id: str = "task_05_planted_defects",
) -> TaskResult:
    """Verify MUST rules catch deliberately planted defects."""
    started = time.perf_counter()
    payload = _load_fixture(fixture_path)
    passage = ReadingPassage.model_validate(payload["passage"])
    items = tuple(ReadingItem.model_validate(item) for item in payload["items"])
    expected_failures: set[str] = set(payload.get("expected_rule_failures", []))
    rules = _rules_for_fixture(payload)

    detected: set[str] = set()
    for index, item in enumerate(items):
        context = ItemRuleContext(passage=passage, item=item, item_index=index, all_items=items)
        for rule_code, rule in rules:
            result = rule.evaluate(context)
            if not result.passed and result.severity.value == "must":
                detected.add(rule_code)

    recall = 1.0 if not expected_failures else len(detected & expected_failures) / len(expected_failures)
    false_positives = detected - expected_failures
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    return TaskResult(
        task_id=task_id,
        model_profile=model_profile,
        mode=mode,
        passed=recall >= 1.0 and not false_positives,
        wall_time_ms=elapsed_ms,
        metrics=[
            TaskMetric(
                name="planted_defect_recall",
                value=recall,
                detail={
                    "fixture": fixture_path.name,
                    "expected": sorted(expected_failures),
                    "detected": sorted(detected),
                    "false_positives": sorted(false_positives),
                },
            )
        ],
        notes="Deterministic L1 planted-defect check. Critic scoring deferred to live mode.",
    )
