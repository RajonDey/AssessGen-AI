"""Kokoro TTS helpers for Listening demo synthesis (optional dependency)."""

from __future__ import annotations

import io
import json
import logging
import re
from typing import Any

import numpy as np

log = logging.getLogger("assessgen")

SAMPLE_RATE = 24_000
GAP_SECONDS = 0.35
PAUSE_TAG = re.compile(r"\[PAUSE:(\d+(?:\.\d+)?)\]", re.IGNORECASE)

# Instructor (N1) is never a conversation voice — same id across parts still maps here.
NARRATOR_LANG_VOICE = ("b", "bf_isabella")
CHARACTER_VOICES: list[tuple[str, str]] = [
    ("b", "bf_emma"),
    ("b", "bm_george"),
    ("a", "af_heart"),
    ("a", "am_adam"),
    ("a", "af_bella"),
    ("b", "bm_lewis"),
]

# (accent, gender) -> (lang_code, voice_id) for conversation speakers
VOICE_MAP: dict[tuple[str, str], tuple[str, str]] = {
    ("british", "female"): ("b", "bf_emma"),
    ("british", "male"): ("b", "bm_george"),
    ("american", "female"): ("a", "af_heart"),
    ("american", "male"): ("a", "am_adam"),
    ("australian", "female"): ("a", "af_heart"),  # Kokoro gap — approximate
    ("australian", "male"): ("a", "am_adam"),
    ("new_zealand", "female"): ("b", "bf_emma"),
    ("new_zealand", "male"): ("b", "bm_george"),
}


class TtsNotInstalledError(RuntimeError):
    """Raised when kokoro is not installed in the environment."""


class ScriptValidationError(ValueError):
    """Raised when uploaded listening paper is not TTS-ready."""


def parse_listening_payload(raw: str | bytes) -> dict[str, Any]:
    """Parse JSON or markdown-fenced JSON into a listening paper dict."""
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="replace")
    else:
        text = raw
    text = text.strip()
    if not text:
        raise ScriptValidationError("Empty upload")

    last_error: Exception | None = None
    whole = _try_load_json_object(text)
    if whole is not None:
        paper = _coerce_listening_paper(whole)
        if paper is not None:
            return paper
        # Valid JSON but not a listening paper. Do not extract an inner ```json
        # fence from document — Generate downloads embed an escaped copy there.
        extracted = _extract_speakers_and_turns(text)
        if extracted is not None:
            return extracted
        raise ScriptValidationError(_tts_parse_failure_message(text, None))

    text = _extract_json_candidate(text)

    for candidate in _json_candidates(text):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        paper = _coerce_listening_paper(data)
        if paper is not None:
            if candidate != text:
                log.warning("tts.json_repaired")
            return paper

    repaired = _try_repair_truncated_json(text)
    if repaired is not None:
        log.warning("tts.json_repaired_truncated_document")
        return repaired

    extracted = _extract_speakers_and_turns(text)
    if extracted is not None:
        log.warning("tts.json_extracted_turns_after_parse_failure")
        return extracted

    raise ScriptValidationError(_tts_parse_failure_message(text, last_error)) from last_error


def _tts_parse_failure_message(text: str, last_error: Exception | None) -> str:
    has_object = "{" in text
    looks_prose = text.lstrip().startswith("#") or "Speaker " in text[:800]
    if not has_object:
        return (
            "This file is not TTS-ready JSON. Listening audio needs a JSON object with "
            "speakers[] and script.turns[] — use Download JSON from Generate. "
            "Prose Markdown (headings or 'Speaker 1 (S1):' lines) cannot be synthesized."
        )
    if looks_prose:
        return (
            "This Markdown has no speakers[] / script.turns[] JSON. "
            "Re-generate Listening and download the JSON file, not the Markdown paper."
        )
    detail = last_error or "unknown JSON error"
    return (
        f"Could not parse speakers[] and script.turns[] ({detail}). "
        "Upload Generate's JSON download, or a .md file that contains a JSON object with turns."
    )


def _try_load_json_object(text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _extract_json_candidate(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    elif text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, count=1, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def _json_candidates(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for cand in (text, _soften_llm_json(text), _json_repair_text(text)):
        if not cand or cand in seen:
            continue
        seen.add(cand)
        out.append(cand)
        closed = _close_open_containers(cand.rstrip().rstrip(","))
        if closed and closed not in seen:
            seen.add(closed)
            out.append(closed)
    return out


def _json_repair_text(text: str) -> str | None:
    try:
        from json_repair import repair_json
    except ImportError:
        return None
    try:
        repaired = repair_json(text, return_objects=False)
    except Exception:  # noqa: BLE001 — fall through to other repair paths
        return None
    return str(repaired) if repaired else None


def _soften_llm_json(text: str) -> str:
    """Fix frequent generator JSON mistakes (missing colons/commas, smart quotes)."""
    softened = (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )
    softened = re.sub(r",\s*([}\]])", r"\1", softened)
    softened = re.sub(r"\}\s*\{", "},{", softened)
    # Missing colon: "1" "Green Park"  or  "word_count" 620
    softened = re.sub(
        r'("(?:\\.|[^"\\])*")[ \t]+("(?:\\.|[^"\\])*")',
        r"\1: \2",
        softened,
    )
    softened = re.sub(
        r'("(?:\\.|[^"\\])*")[ \t]+(-?\d+(?:\.\d+)?|true|false|null)\b',
        r"\1: \2",
        softened,
        flags=re.IGNORECASE,
    )
    # Missing comma between object fields
    softened = re.sub(
        r'(:\s*"(?:\\.|[^"\\])*")\s*\n(\s*")',
        r"\1,\n\2",
        softened,
    )
    softened = re.sub(
        r"(:\s*(?:-?\d+(?:\.\d+)?|true|false|null))\s*\n(\s*\")",
        r"\1,\n\2",
        softened,
        flags=re.IGNORECASE,
    )
    return softened


def _coerce_listening_paper(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    inner = data.get("content")
    if isinstance(inner, dict) and (inner.get("script") or inner.get("speakers")):
        data = inner
    if data.get("script") or data.get("speakers"):
        return data
    return None


def _extract_speakers_and_turns(text: str) -> dict[str, Any] | None:
    """Last-resort: pull speakers[] and script.turns[] even if later JSON is broken."""
    speakers = _extract_json_array_after_key(text, "speakers")
    turns = _extract_json_array_after_key(text, "turns")
    if not isinstance(turns, list) or not turns:
        return None
    paper: dict[str, Any] = {
        "type": "listening",
        "speakers": speakers if isinstance(speakers, list) else [],
        "script": {"turns": turns},
    }
    if not paper["speakers"]:
        ids: list[str] = []
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            sid = str(turn.get("speaker") or "").strip()
            if sid and sid.upper() != "PAUSE" and sid not in ids:
                ids.append(sid)
        paper["speakers"] = [
            {"id": sid, "gender": "female", "accent": "british"} for sid in ids
        ]
    return paper


def _extract_json_array_after_key(text: str, key: str) -> list[Any] | None:
    match = re.search(rf'"{re.escape(key)}"\s*:', text)
    if not match:
        return None
    i = text.find("[", match.end())
    if i == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for j, ch in enumerate(text[i:], start=i):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                blob = text[i : j + 1]
                for candidate in (blob, _soften_llm_json(blob), _json_repair_text(blob)):
                    if not candidate:
                        continue
                    try:
                        parsed = json.loads(candidate)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(parsed, list):
                        return parsed
                return None
    return None


def _try_repair_truncated_json(text: str) -> dict[str, Any] | None:
    """Repair common generator truncations (bad parts close / unclosed document)."""
    candidates = [text]

    # 1) Mistaken `},` closing the parts array → `],`
    fixed_parts = re.sub(
        r'("parts"\s*:\s*\[[\s\S]*?\n\s*\})\s*\n(\s*)\},',
        r"\1\n\2],",
        text,
        count=1,
    )
    if fixed_parts != text:
        candidates.append(fixed_parts)
    # Also handle compact single-line-ish closes: `}\n  },` after parts
    fixed_parts2 = re.sub(r'("parts"\s*:\s*\[[\s\S]*?\})\s*\},', r"\1],", text, count=1)
    if fixed_parts2 != text:
        candidates.append(fixed_parts2)

    expanded: list[str] = []
    for cand in candidates:
        expanded.append(cand)
        # 2) Drop truncated trailing "document" field
        for marker in ('\n  "document":', '\n  "document" :', ',\n  "document":', ',"document":'):
            idx = cand.find(marker)
            if idx == -1:
                continue
            head = cand[:idx].rstrip().rstrip(",")
            closed = _close_open_containers(head)
            if closed is not None:
                expanded.append(closed)

        closed_full = _close_open_containers(cand.rstrip().rstrip(","))
        if closed_full is not None:
            expanded.append(closed_full)

    seen: set[str] = set()
    for cand in expanded:
        if cand in seen:
            continue
        seen.add(cand)
        try:
            data = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and (data.get("script") or data.get("speakers")):
            paper = _coerce_listening_paper(data)
            if paper is not None:
                return paper
    return None


def _close_open_containers(text: str) -> str | None:
    """Append missing }/] if the string is not mid-quote; else None."""
    stack: list[str] = []
    in_str = False
    esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in "}]":
            if not stack or stack[-1] != ch:
                return None
            stack.pop()
    if in_str:
        return None
    return text + "".join(reversed(stack))


def validate_tts_script(paper: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized turns; raise if speakers/turns missing."""
    speakers_raw = paper.get("speakers")
    script = paper.get("script")
    if not isinstance(speakers_raw, list) or not speakers_raw:
        raise ScriptValidationError("Missing speakers[] — required for TTS voice assignment")
    if not isinstance(script, dict):
        raise ScriptValidationError("Missing script object")
    turns = script.get("turns")
    if not isinstance(turns, list) or not turns:
        raise ScriptValidationError("Missing script.turns[] — required for TTS")

    speakers: dict[str, dict[str, Any]] = {}
    for sp in speakers_raw:
        if not isinstance(sp, dict) or not sp.get("id"):
            continue
        speakers[str(sp["id"])] = sp

    if not speakers:
        raise ScriptValidationError("No valid speaker ids found")

    voice_by_id = _assign_speaker_voices(speakers)

    normalized: list[dict[str, Any]] = []
    for idx, turn in enumerate(turns):
        if not isinstance(turn, dict):
            raise ScriptValidationError(f"script.turns[{idx}] must be an object")
        sid = str(turn.get("speaker") or "").strip()
        text = str(turn.get("text") or "").strip()
        if not sid:
            raise ScriptValidationError(f"script.turns[{idx}] missing speaker")
        if not text:
            raise ScriptValidationError(f"script.turns[{idx}] missing text")
        pause_seconds = _pause_seconds(turn, text, sid)
        if pause_seconds is not None:
            normalized.append(
                {
                    "index": idx,
                    "speaker": "PAUSE",
                    "text": f"[PAUSE:{pause_seconds:g}]",
                    "pause_seconds": pause_seconds,
                    "lang": "",
                    "voice": "",
                    "accent": "",
                    "gender": "",
                }
            )
            continue
        if sid not in speakers:
            raise ScriptValidationError(f"script.turns[{idx}] speaker {sid!r} not in speakers[]")
        sp = speakers[sid]
        lang, voice = voice_by_id.get(sid, ("a", "af_heart"))
        accent = str(sp.get("accent") or "american").lower().replace(" ", "_")
        gender = str(sp.get("gender") or "female").lower()
        normalized.append(
            {
                "index": idx,
                "speaker": sid,
                "text": text,
                "lang": lang,
                "voice": voice,
                "accent": accent,
                "gender": gender,
            }
        )
    return normalized


def _is_narrator_speaker(sid: str, sp: dict[str, Any] | None = None) -> bool:
    upper = sid.strip().upper()
    if upper in {"N1", "NARRATOR"} or upper.endswith("_N1"):
        return True
    if isinstance(sp, dict) and str(sp.get("role") or "").strip().lower() == "narrator":
        return True
    return False


def _assign_speaker_voices(speakers: dict[str, dict[str, Any]]) -> dict[str, tuple[str, str]]:
    """N1 always gets the instructor voice; characters get unused Kokoro voices."""
    assigned: dict[str, tuple[str, str]] = {}
    used: set[str] = set()
    for sid, sp in speakers.items():
        if _is_narrator_speaker(sid, sp):
            assigned[sid] = NARRATOR_LANG_VOICE
            used.add(NARRATOR_LANG_VOICE[1])
    for sid, sp in speakers.items():
        if sid in assigned:
            continue
        accent = str(sp.get("accent") or "american").lower().replace(" ", "_")
        gender = str(sp.get("gender") or "female").lower()
        preferred = VOICE_MAP.get((accent, gender), ("a", "af_heart"))
        if preferred[1] not in used:
            assigned[sid] = preferred
            used.add(preferred[1])
            continue
        for cand in CHARACTER_VOICES:
            if cand[1] not in used:
                assigned[sid] = cand
                used.add(cand[1])
                break
        else:
            assigned[sid] = preferred
    return assigned


def _pause_seconds(turn: dict[str, Any], text: str, speaker: str) -> float | None:
    raw = turn.get("pause_seconds")
    if raw is not None:
        try:
            seconds = float(raw)
        except (TypeError, ValueError):
            return None
        if seconds > 0:
            return seconds
    match = PAUSE_TAG.search(text)
    if match:
        return float(match.group(1))
    if speaker.upper() == "PAUSE":
        raise ScriptValidationError(
            f"PAUSE turn must use text like [PAUSE:30] or pause_seconds, got {text!r}"
        )
    return None


def _require_kokoro() -> Any:
    try:
        from kokoro import KPipeline  # type: ignore[import-untyped]
    except ImportError as exc:
        raise TtsNotInstalledError(
            "Kokoro is not installed. Run: "
            "uv sync --extra tts  (and apt install espeak-ng)"
        ) from exc
    return KPipeline


def synthesize_wav_bytes(paper: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """Synthesize a WAV from a listening paper. Returns (wav_bytes, meta)."""
    turns = validate_tts_script(paper)
    KPipeline = _require_kokoro()

    pipelines: dict[str, Any] = {}
    audio_parts: list[np.ndarray] = []
    gap = np.zeros(int(SAMPLE_RATE * GAP_SECONDS), dtype=np.float32)

    for turn in turns:
        pause = turn.get("pause_seconds")
        if pause:
            log.info("tts.pause index=%s seconds=%s", turn["index"], pause)
            audio_parts.append(np.zeros(int(SAMPLE_RATE * float(pause)), dtype=np.float32))
            continue
        lang = turn["lang"]
        if lang not in pipelines:
            log.info("tts.pipeline_init lang=%s", lang)
            pipelines[lang] = KPipeline(lang_code=lang)
        pipe = pipelines[lang]
        log.info(
            "tts.turn index=%s speaker=%s voice=%s chars=%s",
            turn["index"],
            turn["speaker"],
            turn["voice"],
            len(turn["text"]),
        )
        chunks: list[np.ndarray] = []
        for _, _, audio in pipe(turn["text"], voice=turn["voice"], speed=1.0):
            chunks.append(np.asarray(audio, dtype=np.float32))
        if not chunks:
            continue
        audio_parts.append(np.concatenate(chunks))
        audio_parts.append(gap)

    if not audio_parts:
        raise ScriptValidationError("No audio was produced from script turns")

    # Drop trailing gap
    if len(audio_parts) >= 2 and len(audio_parts[-1]) == len(gap):
        wav = np.concatenate(audio_parts[:-1])
    else:
        wav = np.concatenate(audio_parts)

    buf = io.BytesIO()
    try:
        import soundfile as sf  # type: ignore[import-untyped]
    except ImportError as exc:
        raise TtsNotInstalledError(
            "soundfile is not installed. Run: uv sync --extra tts"
        ) from exc

    sf.write(buf, wav, SAMPLE_RATE, format="WAV")
    meta = {
        "turns": len(turns),
        "duration_seconds": round(float(len(wav) / SAMPLE_RATE), 2),
        "sample_rate": SAMPLE_RATE,
        "voices": [
            {"speaker": t["speaker"], "voice": t["voice"], "lang": t["lang"]}
            for t in turns
            if not t.get("pause_seconds")
        ],
    }
    return buf.getvalue(), meta
