"""R-PASS-009 tests."""

from app.modules.ielts.reading.rules.r_pass_009 import PassageNoContradictionRule
from tests.unit.modules.ielts.reading.conftest import make_context


def test_consistent_claims_pass() -> None:
    text = "The population was 2 million. The city grew steadily after 1990."
    context = make_context(paragraphs=[("A", text)])
    assert PassageNoContradictionRule().evaluate(context).passed


def test_contradictory_subject_values_fail() -> None:
    text = "The population was 2 million. Later, the population was 5 million."
    context = make_context(paragraphs=[("A", text)])
    result = PassageNoContradictionRule().evaluate(context)
    assert not result.passed
    assert result.detail["contradictions"]
