"""R-PASS-004 tests."""

from app.modules.ielts.reading.rules.r_pass_004 import PassageReadabilityRule
from tests.unit.modules.ielts.reading.conftest import make_context


def test_readability_rule_returns_grade_detail() -> None:
    text = (
        "Urban agriculture transforms vacant lots into productive gardens. "
        "Researchers document yield gains across temperate climates. "
        "Policy makers now fund pilot programs in several major cities."
    )
    context = make_context(paragraphs=[("A", text)], target_band=7.0)
    result = PassageReadabilityRule().evaluate(context)
    assert "flesch_kincaid_grade" in result.detail
    assert result.rule_code == "R-PASS-004"


def test_empty_passage_does_not_raise() -> None:
    context = make_context(paragraphs=[("A", " ")], word_count_min=1, word_count_max=10000)
    PassageReadabilityRule().evaluate(context)
