"""Unit tests for planted-defect benchmark fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from app.modules.ielts.reading.item_context import ItemRuleContext
from app.modules.ielts.listening.rules.r_list_001 import ListeningVerbatimAnswerRule
from app.modules.ielts.reading.rules.r_comp_001 import CompletionVerbatimAnswerRule
from app.modules.ielts.reading.rules.r_comp_002 import CompletionWordLimitRule
from app.modules.ielts.reading.schemas import ReadingItem, ReadingPassage

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "evals/benchmarks/planted_defects"


def _evaluate_fixture(path: Path, rule) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    passage = ReadingPassage.model_validate(payload["passage"])
    items = tuple(ReadingItem.model_validate(item) for item in payload["items"])
    detected: set[str] = set()
    for index, item in enumerate(items):
        context = ItemRuleContext(passage=passage, item=item, item_index=index, all_items=items)
        result = rule.evaluate(context)
        if not result.passed and result.severity.value == "must":
            detected.add(result.rule_code)
    return detected


def test_planted_non_verbatim_answer_is_detected() -> None:
    fixture = FIXTURES / "reading_non_verbatim_answer.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    expected = set(payload["expected_rule_failures"])
    detected = _evaluate_fixture(fixture, CompletionVerbatimAnswerRule())
    assert detected == expected


def test_planted_word_limit_exceeded_is_detected() -> None:
    fixture = FIXTURES / "reading_word_limit_exceeded.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    expected = set(payload["expected_rule_failures"])
    detected = _evaluate_fixture(fixture, CompletionWordLimitRule())
    assert detected == expected


def test_planted_listening_non_verbatim_is_detected() -> None:
    fixture = FIXTURES / "listening_non_verbatim_answer.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    expected = set(payload["expected_rule_failures"])
    detected = _evaluate_fixture(fixture, ListeningVerbatimAnswerRule())
    assert detected == expected
