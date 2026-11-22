"""JSON / document coerce helpers for messy LLM output."""

from app.llm.client import coerce_model_output, parse_json_object


def test_parse_json_object_strips_fence_and_prose() -> None:
    raw = 'Here you go:\n```json\n{"a": 1, "b": [2]}\n```\nthanks'
    assert parse_json_object(raw) == {"a": 1, "b": [2]}


def test_parse_json_object_trailing_comma() -> None:
    raw = '{"a": 1, "b": 2,}'
    assert parse_json_object(raw) == {"a": 1, "b": 2}


def test_coerce_markdown_document() -> None:
    raw = "# Reading Practice\n\n## Passage\n\nCities need parks for health.\n"
    out = coerce_model_output(raw)
    assert out["format"] == "markdown"
    assert "Cities need parks" in out["document"]


def test_coerce_valid_json_keeps_structure() -> None:
    raw = '{"type": "reading", "sections": [{"title": "A"}], "answer_key": {"1": "TRUE"}}'
    out = coerce_model_output(raw)
    assert out["format"] == "json"
    assert out["type"] == "reading"
    assert "document" in out
