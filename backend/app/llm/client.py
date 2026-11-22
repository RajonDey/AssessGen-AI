"""Thin LLM client — Ollama or OpenAI-compatible chat APIs."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal, Protocol

import httpx

from app.config import Settings

log = logging.getLogger("assessgen")

_TRAILING_COMMA = re.compile(r",\s*([}\]])")
OutputFormat = Literal["json", "markdown", "text"]

# Models that spend tokens on a hidden chain-of-thought (`message.thinking`).
# qwen2.5 is not in this family — do not send `think` for it.
def model_uses_thinking(model: str) -> bool:
    base = model.lower().split("/")[-1].split(":")[0]
    return (
        base.startswith("gemma4")
        or base.startswith("qwen3")
        or base.startswith("deepseek-r1")
        or base.startswith("gpt-oss")
        or base.startswith("qwq")
    )


def extract_ollama_message_text(data: dict[str, Any]) -> str:
    """Prefer `content`; Gemma 4 often leaves it empty and fills `thinking`."""
    message = data.get("message")
    if not isinstance(message, dict):
        message = {}
    content = str(message.get("content") or "").strip()
    if content:
        return content
    thinking = str(
        message.get("thinking") or message.get("reasoning") or data.get("thinking") or ""
    ).strip()
    if thinking:
        log.info("ollama.content_empty_using_thinking chars=%s", len(thinking))
    return thinking


def _httpx_timeout(seconds: float) -> httpx.Timeout:
    """Build httpx timeout. ``seconds <= 0`` disables read timeout (wait for Ollama)."""
    connect = 60.0
    if seconds <= 0:
        return httpx.Timeout(None, connect=connect)
    return httpx.Timeout(
        connect=min(connect, seconds),
        read=seconds,
        write=min(connect, seconds),
        pool=min(connect, seconds),
    )


async def _complete_json_with_retry(
    chat_fn: Any,
    *,
    model: str,
    system: str,
    user: str,
) -> dict[str, Any]:
    """JSON for planner/reviewer. Thinking models: think on + JSON, then think off free-form.

    ``think: false`` plus ``format: json`` is broken on some Gemma 4 Ollama builds, so the
    last attempt drops both and relies on parse_json_object.
    """
    thinking = model_uses_thinking(model)
    json_predict = 4096 if thinking else 2048
    last_raw = ""
    for attempt in range(1, 3):
        last_raw = await chat_fn(
            model=model,
            system=system,
            user=user,
            force_json=True,
            think=True if thinking else None,
            num_predict=json_predict,
        )
        if not str(last_raw).strip():
            log.warning("json.empty_content attempt=%s model=%s", attempt, model)
            continue
        try:
            return parse_json_object(last_raw)
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("json.parse_failed attempt=%s: %s", attempt, exc)

    last_raw = await chat_fn(
        model=model,
        system=system,
        user=user,
        force_json=False,
        think=False if thinking else None,
        num_predict=json_predict,
    )
    if str(last_raw).strip():
        try:
            return parse_json_object(last_raw)
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("json.parse_failed after free-form retry: %s", exc)

    log.warning("json.giving_up wrapping as text document")
    from app.content.validate import EMPTY_DOCUMENT_MARKER

    return document_payload(last_raw or EMPTY_DOCUMENT_MARKER, preferred="text")


class LLMClient(Protocol):
    async def complete_json(self, *, model: str, system: str, user: str) -> dict[str, Any]: ...

    async def complete_document(
        self, *, model: str, system: str, user: str
    ) -> dict[str, Any]: ...


class OllamaClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = _httpx_timeout(timeout)

    async def _chat(
        self,
        *,
        model: str,
        system: str,
        user: str,
        force_json: bool = False,
        num_predict: int | None = None,
        think: bool | None = None,
    ) -> str:
        predict = num_predict if num_predict is not None else (2048 if force_json else 16384)
        payload: dict[str, Any] = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"num_predict": predict},
        }
        if force_json:
            payload["format"] = "json"
        if think is not None and model_uses_thinking(model):
            payload["think"] = think
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}/api/chat", json=payload)
            if response.status_code == 404:
                detail = _ollama_error_detail(response)
                if detail and "not found" in detail.lower():
                    msg = (
                        f"Ollama model {model!r} is not installed ({detail}). "
                        f"Run: ollama pull {model}  — or set OLLAMA_GENERATOR_MODEL / "
                        "OLLAMA_REVIEWER_MODEL in backend/.env to a model from `ollama list`."
                    )
                    raise RuntimeError(msg)
            response.raise_for_status()
            data = response.json()
        return extract_ollama_message_text(data)

    async def complete_json(self, *, model: str, system: str, user: str) -> dict[str, Any]:
        """JSON for planner/reviewer — retry once on empty/invalid, then free-form parse."""
        return await _complete_json_with_retry(
            self._chat,
            model=model,
            system=system,
            user=user,
        )

    async def complete_document(self, *, model: str, system: str, user: str) -> dict[str, Any]:
        """Accept JSON or markdown; retry when the model returns blank or placeholder output.

        Thinking models: disable think for long papers (tokens go to the script, not CoT).
        Last attempt turns think back on in case ``think: false`` is ignored.
        """
        from app.content.validate import has_structured_paper_fields

        thinking = model_uses_thinking(model)
        last_raw = ""
        for attempt in range(1, 4):
            think: bool | None = None
            if thinking:
                # Long papers: spend tokens on the script. Last try restores CoT.
                think = False if attempt < 3 else True
            raw = await self._chat(
                model=model,
                system=system,
                user=user,
                force_json=False,
                num_predict=16384,
                think=think,
            )
            last_raw = raw
            if not str(raw).strip():
                log.warning(
                    "document.empty_raw attempt=%s model=%s think=%s",
                    attempt,
                    model,
                    think,
                )
                continue
            result = coerce_model_output(raw)
            doc = str(result.get("document") or "").strip()
            if has_structured_paper_fields(result) or len(doc) >= 80:
                log.info("document.ok attempt=%s chars=%s think=%s", attempt, len(raw), think)
                return result
            log.warning(
                "document.too_short attempt=%s doc_chars=%s structured=%s",
                attempt,
                len(doc),
                has_structured_paper_fields(result),
            )
        log.warning("document.giving_up model=%s", model)
        return coerce_model_output(last_raw)


class OpenAICompatClient:
    def __init__(self, *, base_url: str, api_key: str, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = _httpx_timeout(timeout)

    async def _chat(
        self,
        *,
        model: str,
        system: str,
        user: str,
        force_json: bool = False,
        num_predict: int | None = None,
        think: bool | None = None,
    ) -> str:
        if not self._api_key:
            msg = "OPENAI_API_KEY is required when LLM_PROVIDER=openai"
            raise RuntimeError(msg)
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if force_json:
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return str(data["choices"][0]["message"]["content"] or "")

    async def complete_json(self, *, model: str, system: str, user: str) -> dict[str, Any]:
        return await _complete_json_with_retry(
            self._chat,
            model=model,
            system=system,
            user=user,
        )

    async def complete_document(self, *, model: str, system: str, user: str) -> dict[str, Any]:
        raw = await self._chat(model=model, system=system, user=user, force_json=False)
        return coerce_model_output(raw)


def _ollama_error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict) and body.get("error"):
            return str(body["error"])
    except (json.JSONDecodeError, ValueError):
        pass
    return response.text.strip()[:200]


def coerce_model_output(raw: str) -> dict[str, Any]:
    """Prefer JSON object when valid; otherwise wrap as a readable document."""
    from app.content.validate import EMPTY_DOCUMENT_MARKER

    text = raw.strip()
    if not text:
        return document_payload(EMPTY_DOCUMENT_MARKER, preferred="text")

    # Try fenced json first, then whole object
    try:
        parsed = parse_json_object(text)
        # If model returned {"document": "..."} already, normalize
        if "document" in parsed or "sections" in parsed or "parts" in parsed or "prompt" in parsed:
            if "format" not in parsed:
                parsed["format"] = "json"
            if "document" not in parsed:
                parsed["document"] = _json_as_markdown(parsed)
            return parsed
        # Tiny planner-like objects without paper fields — still OK
        parsed.setdefault("format", "json")
        parsed.setdefault("document", _json_as_markdown(parsed))
        return parsed
    except (json.JSONDecodeError, ValueError):
        preferred: OutputFormat = "markdown" if _looks_like_markdown(text) else "text"
        log.info("model.output_as_%s chars=%s", preferred, len(text))
        return document_payload(text, preferred=preferred)


def document_payload(text: str, *, preferred: OutputFormat) -> dict[str, Any]:
    return {
        "format": preferred,
        "document": text.strip(),
        "type": "document",
    }


def _looks_like_markdown(text: str) -> bool:
    markers = ("# ", "## ", "### ", "- ", "* ", "```", "**")
    return any(m in text for m in markers)


def _json_as_markdown(data: dict[str, Any]) -> str:
    """Human-readable dump when structured JSON is present."""
    lines = ["# Generated practice content", ""]
    title = data.get("title") or data.get("id")
    if title:
        lines.append(f"**Title:** {title}")
        lines.append("")
    if data.get("document"):
        return str(data["document"])
    lines.append("```json")
    lines.append(json.dumps(data, indent=2, ensure_ascii=False))
    lines.append("```")
    return "\n".join(lines)


def parse_json_object(content: str) -> dict[str, Any]:
    """Parse a JSON object from model output with light cleanup."""
    text = _normalize_json_text(content)
    try:
        parsed: Any = json.loads(text)
    except json.JSONDecodeError:
        softened = _TRAILING_COMMA.sub(r"\1", text)
        parsed = json.loads(softened)

    if not isinstance(parsed, dict):
        msg = "Model returned JSON that is not an object"
        raise ValueError(msg)
    return parsed


def _normalize_json_text(content: str) -> str:
    text = content.strip()
    if not text:
        raise ValueError("Model returned empty content")

    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")
    return text[start : end + 1]


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "openai":
        return OpenAICompatClient(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            timeout=settings.llm_timeout_seconds,
        )
    return OllamaClient(settings.ollama_base_url, settings.llm_timeout_seconds)


def generator_model(settings: Settings) -> str:
    if settings.llm_provider == "openai":
        return settings.openai_generator_model
    return settings.ollama_generator_model


def reviewer_model(settings: Settings) -> str:
    if settings.llm_provider == "openai":
        return settings.openai_reviewer_model
    return settings.ollama_reviewer_model
