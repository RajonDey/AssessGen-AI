"""Unit tests for Listening TTS payload parsing (no Kokoro required)."""

import json

import pytest

from app.tts.kokoro_synth import (
    ScriptValidationError,
    parse_listening_payload,
    validate_tts_script,
)


SAMPLE = """```json
{
  "type": "listening",
  "speakers": [
    {"id": "S1", "role": "resident", "gender": "female", "accent": "british"},
    {"id": "S2", "role": "planner", "gender": "male", "accent": "american"}
  ],
  "script": {
    "turns": [
      {"speaker": "S1", "text": "Hello there."},
      {"speaker": "S2", "text": "Good morning."}
    ]
  }
}
```"""


def test_prose_markdown_explains_missing_json_turns() -> None:
    prose = """# IELTS Listening Practice Test - Part 1

Speaker 1 (S1): Good morning, Kate!
Kate (S2): Hi there, Tom.
"""
    with pytest.raises(ScriptValidationError, match="TTS-ready JSON"):
        parse_listening_payload(prose)


def test_parse_generate_json_download_ignores_inner_document_fence() -> None:
    """Generate JSON embeds a ```json copy inside document — use the outer object."""
    inner = {
        "type": "listening",
        "speakers": [{"id": "S1", "gender": "female", "accent": "british"}],
        "script": {"turns": [{"speaker": "S1", "text": "Welcome to the park."}]},
    }
    payload = {
        **inner,
        "format": "json",
        "document": "# Generated practice content\n\n```json\n"
        + json.dumps(inner, indent=2)
        + "\n```",
        "_meta": {"module": "listening", "generator_model": "qwen2.5:7b"},
    }
    paper = parse_listening_payload(json.dumps(payload, indent=2))
    assert paper["script"]["turns"][0]["text"] == "Welcome to the park."
    assert paper["speakers"][0]["id"] == "S1"


def test_parse_fenced_markdown_json() -> None:
    paper = parse_listening_payload(SAMPLE)
    assert paper["type"] == "listening"
    assert len(paper["speakers"]) == 2


def test_validate_assigns_voices() -> None:
    paper = parse_listening_payload(SAMPLE)
    turns = validate_tts_script(paper)
    assert turns[0]["voice"] == "bf_emma"
    assert turns[0]["lang"] == "b"
    assert turns[1]["voice"] == "am_adam"
    assert turns[1]["lang"] == "a"


def test_narrator_voice_distinct_from_same_accent_character() -> None:
    paper = {
        "speakers": [
            {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
            {"id": "S1", "role": "clerk", "gender": "male", "accent": "british"},
            {"id": "S2", "role": "customer", "gender": "female", "accent": "british"},
        ],
        "script": {
            "turns": [
                {"speaker": "N1", "text": "Look at questions 1 to 6."},
                {"speaker": "S1", "text": "Good morning."},
                {"speaker": "S2", "text": "Hello."},
            ]
        },
    }
    turns = validate_tts_script(paper)
    voices = {t["speaker"]: t["voice"] for t in turns}
    assert voices["N1"] == "bf_isabella"
    assert voices["S1"] == "bm_george"
    assert voices["S2"] == "bf_emma"
    assert len(set(voices.values())) == 3


def test_prefixed_narrator_keeps_instructor_voice() -> None:
    paper = {
        "speakers": [
            {"id": "P1_N1", "role": "narrator", "gender": "female", "accent": "british"},
            {"id": "P2_N1", "role": "narrator", "gender": "female", "accent": "british"},
            {"id": "P1_S1", "gender": "male", "accent": "british"},
        ],
        "script": {
            "turns": [
                {"speaker": "P1_N1", "text": "Now look at Part 1."},
                {"speaker": "P1_S1", "text": "Hello."},
                {"speaker": "P2_N1", "text": "Now look at Part 2."},
            ]
        },
    }
    turns = validate_tts_script(paper)
    assert turns[0]["voice"] == "bf_isabella"
    assert turns[2]["voice"] == "bf_isabella"
    assert turns[1]["voice"] != "bf_isabella"


def test_missing_turns_fails() -> None:
    with pytest.raises(ScriptValidationError, match="script.turns"):
        validate_tts_script({"speakers": [{"id": "S1"}], "script": {}})


def test_pause_turn_allowed_without_speakers_entry() -> None:
    paper = {
        "speakers": [{"id": "S1", "gender": "female", "accent": "british"}],
        "script": {
            "turns": [
                {"speaker": "PAUSE", "text": "[PAUSE:30]"},
                {"speaker": "S1", "text": "Welcome to the centre."},
                {"speaker": "PAUSE", "text": "[PAUSE:20]"},
            ]
        },
    }
    turns = validate_tts_script(paper)
    assert turns[0]["speaker"] == "PAUSE"
    assert turns[0]["pause_seconds"] == 30
    assert turns[1]["voice"] == "bf_emma"
    assert turns[2]["pause_seconds"] == 20
    silence = sum(float(t.get("pause_seconds") or 0) for t in turns)
    assert silence == 50


def test_pause_seconds_field_without_tag() -> None:
    paper = {
        "speakers": [{"id": "S1", "gender": "male", "accent": "american"}],
        "script": {
            "turns": [
                {"speaker": "PAUSE", "text": "hold", "pause_seconds": 15},
                {"speaker": "S1", "text": "Hello."},
            ]
        },
    }
    turns = validate_tts_script(paper)
    assert turns[0]["pause_seconds"] == 15
    assert turns[0]["text"] == "[PAUSE:15]"


def test_pause_speaker_without_duration_fails() -> None:
    with pytest.raises(ScriptValidationError, match="PAUSE"):
        validate_tts_script(
            {
                "speakers": [{"id": "S1", "gender": "female", "accent": "british"}],
                "script": {"turns": [{"speaker": "PAUSE", "text": "please wait"}]},
            }
        )


def test_repair_missing_colon_in_answer_key() -> None:
    broken = """{
  "speakers": [{"id": "S1", "gender": "female", "accent": "british"}],
  "script": {
    "turns": [
      {"speaker": "S1", "text": "The park is called Green Park."}
    ]
  },
  "answer_key": {
          "1" "Green Park"
  }
}"""
    paper = parse_listening_payload(broken)
    turns = validate_tts_script(paper)
    assert turns[0]["text"] == "The park is called Green Park."


def test_repair_missing_comma_between_fields() -> None:
    broken = """{
  "speakers": [{"id": "S1", "gender": "male", "accent": "american"}],
  "script": {"turns": [
      {"speaker": "S1"
      "text": "Hello there."}
  ]}
}"""
    paper = parse_listening_payload(broken)
    turns = validate_tts_script(paper)
    assert turns[0]["speaker"] == "S1"
    assert turns[0]["text"] == "Hello there."


def test_parse_wrapped_generate_response() -> None:
    wrapped = {
        "module": "listening",
        "content": {
            "speakers": [{"id": "S1", "gender": "female", "accent": "british"}],
            "script": {"turns": [{"speaker": "S1", "text": "Hi."}]},
        },
    }
    paper = parse_listening_payload(json.dumps(wrapped))
    assert paper["script"]["turns"][0]["text"] == "Hi."


def test_extract_turns_when_later_json_is_broken() -> None:
    broken = """{
  "speakers": [{"id": "S1", "gender": "female", "accent": "british"}],
  "script": {"turns": [{"speaker": "S1", "text": "Welcome."}]},
  "parts": [ this is not json
"""
    paper = parse_listening_payload(broken)
    turns = validate_tts_script(paper)
    assert turns[0]["text"] == "Welcome."


def test_repair_wrong_parts_close_and_truncated_document() -> None:
    broken = """{
  "speakers": [{"id": "S1", "gender": "female", "accent": "british"}],
  "script": {"turns": [{"speaker": "S1", "text": "Hello."}]},
  "parts": [{"partNumber": 1, "questionGroups": []}],
  "answer_key": {"1": "Hello"},
  "document": "# Truncated without close
"""
    # Make parts close with mistaken `},` like the bad export
    broken = broken.replace('"parts": [{"partNumber": 1, "questionGroups": []}],',
                            '"parts": [\n    {"partNumber": 1, "questionGroups": []}\n  },')
    paper = parse_listening_payload(broken)
    turns = validate_tts_script(paper)
    assert len(turns) == 1
    assert turns[0]["text"] == "Hello."
