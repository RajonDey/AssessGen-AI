"""Listening audio synthesis API (Kokoro demo)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.tts.kokoro_synth import (
    ScriptValidationError,
    TtsNotInstalledError,
    parse_listening_payload,
    synthesize_wav_bytes,
)

log = logging.getLogger("assessgen")
router = APIRouter(prefix="/listening", tags=["listening-audio"])


@router.post("/synthesize")
async def synthesize_listening_audio(
    file: UploadFile = File(..., description="Listening JSON or markdown-fenced JSON"),
) -> Response:
    """Upload a TTS-ready Listening script and receive a WAV file."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        paper = parse_listening_payload(raw)
        wav_bytes, meta = synthesize_wav_bytes(paper)
    except ScriptValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TtsNotInstalledError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("listening.synthesize_failed")
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc

    filename = (file.filename or "listening").rsplit(".", 1)[0]
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in filename)[:60] or "listening"
    log.info(
        "listening.synthesize_ok turns=%s duration=%ss",
        meta.get("turns"),
        meta.get("duration_seconds"),
    )
    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'attachment; filename="{safe}.wav"',
            "X-Audio-Duration-Seconds": str(meta.get("duration_seconds", "")),
            "X-Audio-Turns": str(meta.get("turns", "")),
        },
    )


@router.get("/tts-status")
async def tts_status() -> dict:
    """Whether Kokoro is importable in this environment."""
    try:
        import kokoro  # noqa: F401
        import soundfile  # noqa: F401

        return {"available": True, "engine": "kokoro", "sample_rate": 24000}
    except ImportError:
        return {
            "available": False,
            "engine": "kokoro",
            "hint": "uv sync --extra tts && sudo apt install espeak-ng",
        }
