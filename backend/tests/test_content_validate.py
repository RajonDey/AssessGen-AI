"""Tests for empty/unusable generator output detection."""

from app.content.validate import (
    EMPTY_DOCUMENT_MARKER,
    empty_content_finding,
    is_usable_generated_content,
)


def test_empty_placeholder_is_not_usable() -> None:
    content = {
        "format": "text",
        "type": "document",
        "document": EMPTY_DOCUMENT_MARKER,
    }
    assert not is_usable_generated_content(content, module="listening")
    assert not is_usable_generated_content(content, module="reading")


def test_listening_structured_json_is_usable() -> None:
    content = {
        "type": "listening",
        "script": {"turns": [{"speaker": "S1", "text": "Hello."}]},
        "parts": [{"partNumber": 1, "questionGroups": []}],
    }
    assert is_usable_generated_content(content, module="listening")


def test_short_document_not_usable_for_listening() -> None:
    content = {"format": "text", "document": "Too short."}
    assert not is_usable_generated_content(content, module="listening")


def test_listening_markdown_without_turns_is_not_usable() -> None:
    content = {
        "format": "markdown",
        "type": "document",
        "document": "# Listening Part 1\n\n" + ("Kate talks to Tom. " * 20),
    }
    assert not is_usable_generated_content(content, module="listening")


def test_empty_finding_mentions_model() -> None:
    f = empty_content_finding(model="gemma4:e2b")
    assert f.code == "GEN-EMPTY"
    assert f.severity == "must"
    assert "gemma4:e2b" in f.message
