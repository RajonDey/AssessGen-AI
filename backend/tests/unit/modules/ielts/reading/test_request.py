"""Unit tests for reading request parsing."""


from app.domain.enums import PassageSourceMode
from app.modules.ielts.reading.request import parse_reading_spec, validate_plan_counts


def test_parse_reading_spec_defaults() -> None:
    spec = parse_reading_spec({"module": "reading"})
    assert spec.topic == "General science"
    assert spec.question_count == 13
    assert spec.source_mode == PassageSourceMode.GENERATED


def test_parse_reading_spec_from_nested_spec() -> None:
    spec = parse_reading_spec(
        {
            "spec": {
                "topic": "Climate policy",
                "question_count": 2,
                "source_mode": "adapted",
                "source_text": "x" * 120,
                "license_label": "CC-BY-4.0",
            }
        }
    )
    assert spec.topic == "Climate policy"
    assert spec.question_count == 2
    assert spec.source_mode == PassageSourceMode.ADAPTED


def test_validate_plan_counts() -> None:
    ok, _ = validate_plan_counts(block_total=13, question_count=13)
    assert ok
    bad, reason = validate_plan_counts(block_total=10, question_count=13)
    assert not bad
    assert "10" in reason


def test_parse_reading_spec_requires_source_text_for_ingested() -> None:
    import pytest

    with pytest.raises(ValueError, match="source_text"):
        parse_reading_spec({"spec": {"source_mode": "ingested", "topic": "Test"}})
