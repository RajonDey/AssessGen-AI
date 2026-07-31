"""Passage rule registry integration tests."""

from app.modules.ielts.reading.rules import build_passage_rule_registry
from tests.unit.modules.ielts.reading.conftest import make_context


def test_registry_contains_all_nine_passage_rules() -> None:
    registry = build_passage_rule_registry()
    codes = registry.codes()
    assert codes == tuple(f"R-PASS-{i:03d}" for i in range(1, 10))


def test_registry_runs_all_rules_without_raising() -> None:
    text = (
        "Urban farms supply fresh produce. "
        "The population was 2 million in the latest census. "
        "Researchers published detailed findings about soil quality."
    )
    context = make_context(
        paragraphs=[("A", text), ("B", "A second paragraph adds depth.")],
        word_count_min=1,
        word_count_max=10000,
    )
    report = build_passage_rule_registry().run_all(context)
    assert len(report.results) == 9
