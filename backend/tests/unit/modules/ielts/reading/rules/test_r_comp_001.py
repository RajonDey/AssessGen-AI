"""R-COMP-001 tests."""

from app.modules.ielts.reading.rules.r_comp_001 import CompletionVerbatimAnswerRule
from hypothesis import given
from hypothesis import strategies as st
from tests.unit.modules.ielts.reading.conftest import make_completion_item, make_item_context


def test_verbatim_answer_passes_when_present() -> None:
    item = make_completion_item()
    result = CompletionVerbatimAnswerRule().evaluate(make_item_context(item))
    assert result.passed
    assert result.detail["match"]


def test_verbatim_answer_fails_when_missing() -> None:
    item = make_completion_item(answer="chlorophyll")
    result = CompletionVerbatimAnswerRule().evaluate(make_item_context(item))
    assert not result.passed


@given(st.text())
def test_never_raises_on_arbitrary_stem(text: str) -> None:
    item = make_completion_item(stem=text or "Fill _____.")
    result = CompletionVerbatimAnswerRule().evaluate(make_item_context(item))
    assert result.rule_code == "R-COMP-001"
