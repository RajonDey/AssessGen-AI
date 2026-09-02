"""Optional TTS package (Kokoro)."""

from app.tts.kokoro_synth import (
    ScriptValidationError,
    TtsNotInstalledError,
    parse_listening_payload,
    synthesize_wav_bytes,
    validate_tts_script,
)

__all__ = [
    "ScriptValidationError",
    "TtsNotInstalledError",
    "parse_listening_payload",
    "synthesize_wav_bytes",
    "validate_tts_script",
]
