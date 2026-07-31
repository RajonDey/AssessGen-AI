"""Unit tests for reading source ingest."""

from app.modules.ielts.reading.ingest import ingest_source_text


def test_ingest_splits_paragraphs_and_labels() -> None:
    source = "First paragraph about farms.\n\nSecond paragraph about cities."
    passage = ingest_source_text(source, title="Urban farms")
    assert passage.title == "Urban farms"
    assert [p.label for p in passage.paragraphs] == ["A", "B"]
    assert "farms" in passage.paragraphs[0].text
