"""Ollama thinking-model handling (Gemma 4 empty `content`, salvage `thinking`)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from app.llm.client import (
    OllamaClient,
    extract_ollama_message_text,
    model_uses_thinking,
)


def test_model_uses_thinking_families() -> None:
    assert model_uses_thinking("gemma4:12b")
    assert model_uses_thinking("gemma4:e2b")
    assert model_uses_thinking("qwen3.5:9b")
    assert not model_uses_thinking("qwen2.5:7b")
    assert not model_uses_thinking("gpt-4o-mini")


def test_extract_prefers_content() -> None:
    text = extract_ollama_message_text(
        {"message": {"content": '{"ok": true}', "thinking": "ignore me"}}
    )
    assert text == '{"ok": true}'


def test_extract_falls_back_to_thinking() -> None:
    text = extract_ollama_message_text(
        {"message": {"content": "", "thinking": '{"ok": true}'}}
    )
    assert text == '{"ok": true}'


def test_extract_reasoning_alias() -> None:
    text = extract_ollama_message_text({"message": {"content": "  ", "reasoning": "plan"}})
    assert text == "plan"


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.status_code = 200
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


def _patch_chat_posts(payloads: list[dict[str, Any]]):
    captured: list[dict[str, Any]] = []
    remaining = list(payloads)

    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def post(self, url: str, json: dict[str, Any] | None = None) -> _FakeResponse:
            captured.append(json or {})
            body = remaining.pop(0) if remaining else {"message": {"content": ""}}
            return _FakeResponse(body)

    return captured, patch("app.llm.client.httpx.AsyncClient", _FakeClient)


async def test_complete_document_disables_think_for_gemma() -> None:
    paper = {
        "message": {
            "content": (
                '{"type":"listening","script":{"turns":[{"speaker":"N1","text":"Hello there."}]}}'
            )
        }
    }
    captured, ctx = _patch_chat_posts([paper])
    with ctx:
        client = OllamaClient("http://localhost:11434", 0)
        result = await client.complete_document(
            model="gemma4:12b", system="sys", user="write a paper"
        )
    assert captured[0].get("think") is False
    assert "format" not in captured[0]
    assert result.get("type") == "listening"


async def test_complete_document_last_attempt_reenables_think() -> None:
    empty = {"message": {"content": "", "thinking": ""}}
    paper = {
        "message": {
            "content": '{"type":"listening","script":{"turns":[{"speaker":"N1","text":"Hi"}]}}'
        }
    }
    captured, ctx = _patch_chat_posts([empty, empty, paper])
    with ctx:
        client = OllamaClient("http://localhost:11434", 0)
        await client.complete_document(model="gemma4:12b", system="sys", user="paper")
    assert [c.get("think") for c in captured] == [False, False, True]


async def test_chat_salvages_thinking_when_content_empty() -> None:
    captured, ctx = _patch_chat_posts(
        [{"message": {"content": "", "thinking": '{"reasoning": "ok", "steps": ["a"]}'}}]
    )
    with ctx:
        client = OllamaClient("http://localhost:11434", 0)
        raw = await client._chat(
            model="gemma4:12b",
            system="sys",
            user="plan",
            force_json=True,
            think=True,
        )
    assert captured[0]["think"] is True
    assert captured[0]["format"] == "json"
    assert '"reasoning"' in raw


async def test_qwen25_does_not_send_think() -> None:
    captured, ctx = _patch_chat_posts([{"message": {"content": '{"a": 1}'}}])
    with ctx:
        client = OllamaClient("http://localhost:11434", 0)
        await client.complete_document(model="qwen2.5:7b", system="sys", user="paper")
    assert "think" not in captured[0]


async def test_complete_json_think_on_then_off_for_gemma() -> None:
    empty = {"message": {"content": ""}}
    ok = {"message": {"content": '{"reasoning": "plan", "steps": ["one"]}'}}
    captured, ctx = _patch_chat_posts([empty, empty, ok])
    with ctx:
        client = OllamaClient("http://localhost:11434", 0)
        result = await client.complete_json(model="gemma4:12b", system="sys", user="plan")
    assert captured[0].get("think") is True
    assert captured[0].get("format") == "json"
    assert captured[2].get("think") is False
    assert "format" not in captured[2]
    assert result["reasoning"] == "plan"
