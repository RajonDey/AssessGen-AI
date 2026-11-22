"""Phase 1–5 unit tests: cost gates, skeleton, reading normalize, originality, writing brief."""

from __future__ import annotations

from pathlib import Path

from app.content.cost_ledger import CallCounter, record_run, reset, snapshot
from app.content.listening_skeleton import apply_listening_exam_skeleton, exam_clock_intact
from app.content.originality import check_originality, extract_passage_text
from app.content.reading_normalize import normalize_reading_content
from app.pipeline import (
    _gate_passed_for_revise,
    _should_run_critic,
)
from app.rules.structure import evaluate_structure
from app.schemas.generation import ReviewFinding, ReviewResult


def test_should_run_critic_skips_on_draft_and_must() -> None:
    must = [ReviewFinding(severity="must", message="x", code="L-WC")]
    should = [ReviewFinding(severity="should", message="y", code="L-SP")]
    assert _should_run_critic(quality_mode="draft", skip_llm_review=False, rule_findings=should) is False
    assert _should_run_critic(quality_mode="standard", skip_llm_review=False, rule_findings=must) is False
    assert _should_run_critic(quality_mode="standard", skip_llm_review=False, rule_findings=should) is True
    assert _should_run_critic(quality_mode="standard", skip_llm_review=True, rule_findings=should) is False


def test_gate_passed_for_revise_ignores_should() -> None:
    review = ReviewResult(
        passed=False,
        findings=[ReviewFinding(severity="should", message="nit", code="R-LAB")],
    )
    assert _gate_passed_for_revise(review) is True
    review2 = ReviewResult(
        passed=False,
        findings=[ReviewFinding(severity="must", message="bad", code="L-INTRO")],
    )
    assert _gate_passed_for_revise(review2) is False


def test_listening_skeleton_wraps_content_turns() -> None:
    content = {
        "type": "listening",
        "speakers": [{"id": "S1", "gender": "female", "accent": "british"}],
        "script": {
            "turns": [
                {"speaker": "S1", "text": "Hello " + ("word " * 50)},
                {"speaker": "S1", "text": "More " + ("word " * 50)},
            ]
        },
    }
    assert exam_clock_intact(content["script"]["turns"]) is False
    apply_listening_exam_skeleton(content, part_number=2, topic="libraries", question_start=11)
    turns = content["script"]["turns"]
    assert exam_clock_intact(turns)
    assert content["exam_skeleton_applied"] is True
    assert any(t.get("speaker") == "N1" and "Part 2" in str(t.get("text")) for t in turns)
    assert any(str(t.get("text") or "").upper().find("[PAUSE:40]") >= 0 for t in turns)


def test_reading_normalize_builds_sections_from_markdown() -> None:
    doc = """# Climate
Paragraph one about climate systems and oceans.

Paragraph two continues the academic discussion with more detail.

## Questions 1–2
1. What is mentioned?
2. Which factor?

## Answer key
1. oceans
2. temperature
"""
    content = {"document": doc, "format": "markdown"}
    normalize_reading_content(content)
    assert content["type"] == "reading"
    assert isinstance(content["sections"], list) and content["sections"]
    assert content["sections"][0]["passage"]
    assert content["answer_key"]["1"] == "oceans"


def test_originality_blocks_overlapping_ngram(tmp_path: Path) -> None:
    ref = tmp_path / "ref.txt"
    sentence = "the quick brown fox jumps over the lazy dog and runs away fast today"
    ref.write_text(sentence, encoding="utf-8")
    content = {
        "sections": [
            {"title": "P1", "passage": [sentence], "questionGroups": []},
        ]
    }
    findings = check_originality(content, corpus_dir=str(tmp_path))
    assert any(f.code == "ORIG-8GRAM" and f.severity == "must" for f in findings)


def test_originality_ok_on_unique_text(tmp_path: Path) -> None:
    (tmp_path / "ref.txt").write_text(
        "completely different reference material about ancient pottery techniques",
        encoding="utf-8",
    )
    content = {
        "sections": [
            {
                "title": "P1",
                "passage": [
                    "urban green spaces improve mental health outcomes for city residents "
                    "through daily exposure to trees parks and community gardens nearby"
                ],
                "questionGroups": [],
            }
        ]
    }
    assert extract_passage_text(content)
    findings = check_originality(content, corpus_dir=str(tmp_path))
    assert any(f.code == "ORIG-OK" for f in findings)
    assert not any(f.severity == "must" for f in findings)


def test_writing_requires_visual_brief_not_images() -> None:
    content = {
        "type": "writing",
        "sections": [
            {
                "title": "Part 1",
                "questions": [
                    {
                        "title": "The chart below shows sales.",
                        "question": "Summarise the information.",
                        "minWords": 150,
                        # no images, no brief — short title may still fail W-BRIEF
                    }
                ],
            },
            {
                "title": "Part 2",
                "questions": [
                    {
                        "title": "Some people think X.",
                        "question": "Discuss both views.",
                        "minWords": 250,
                    }
                ],
            },
        ],
    }
    report = evaluate_structure("writing", content)
    assert any(f.code == "W-BRIEF" for f in report.findings)
    assert not any(f.code == "W-IMG" and f.severity == "must" for f in report.findings)

    content["sections"][0]["questions"][0]["visual_brief"] = {
        "type": "bar_chart",
        "description": "Annual sales by region 2010–2020 in millions",
        "data_story": "Compare Asia vs Europe rising then plateau",
    }
    report2 = evaluate_structure("writing", content)
    assert not any(f.code == "W-BRIEF" and f.severity == "must" for f in report2.findings)


def test_tts_block_codes_exclude_answer_quality() -> None:
    from app.rules.structure import TTS_BLOCK_CODES

    assert "L-KEY" not in TTS_BLOCK_CODES
    assert "L-VER" not in TTS_BLOCK_CODES
    assert "L-QC" not in TTS_BLOCK_CODES
    assert "L-PARTS" not in TTS_BLOCK_CODES
    assert "L-WC" in TTS_BLOCK_CODES
    assert "L-INTRO" in TTS_BLOCK_CODES


def test_cap_critic_must_to_should() -> None:
    from app.pipeline import _cap_critic_to_should
    from app.schemas.generation import ReviewFinding, ReviewResult

    raw = ReviewResult(
        passed=False,
        findings=[
            ReviewFinding(severity="must", message="No answer key", code="L-MISSING-KEY"),
            ReviewFinding(severity="should", message="nit", code="STYLE"),
        ],
        summary="incomplete",
    )
    capped = _cap_critic_to_should(raw)
    assert capped.passed is True
    assert all(f.severity == "should" for f in capped.findings)
    assert capped.findings[0].message.startswith("[critic]")


def test_stamp_tts_ready_ignores_answer_musts() -> None:
    from app.pipeline import _stamp_tts_ready
    from app.schemas.generation import ReviewFinding, ReviewResult

    # Minimal script with exam clock — length may still fail; focus on key musts not blocking when script OK
    content = {
        "type": "listening",
        "partNumber": 1,
        "speakers": [{"id": "N1"}, {"id": "S1"}],
        "script": {
            "turns": [
                {"speaker": "N1", "text": "Welcome to this listening practice test. "
                 "Recordings once only. Four parts. Now look at Part 1. You will hear a talk. "
                 "Look at questions 1 to 5."},
                {"speaker": "PAUSE", "text": "[PAUSE:40]"},
                {"speaker": "N1", "text": "Now listen and answer questions 1 to 5."},
                {"speaker": "S1", "text": ("word " * 220).strip()},
                {"speaker": "N1", "text": "Look at questions 6 to 10."},
                {"speaker": "PAUSE", "text": "[PAUSE:25]"},
                {"speaker": "N1", "text": "Now listen and answer questions 6 to 10."},
                {"speaker": "S1", "text": ("word " * 220).strip()},
                {"speaker": "N1", "text": "That is the end of Part 1. Check your answers."},
                {"speaker": "PAUSE", "text": "[PAUSE:60]"},
            ]
        },
        "parts": [{"partNumber": 1, "questionGroups": [{"questions": [{"number": i, "type": "text"} for i in range(1, 11)]}]}],
        "answer_key": {},
    }
    review = ReviewResult(
        passed=False,
        findings=[ReviewFinding(severity="must", message="no key", code="L-KEY")],
    )
    _stamp_tts_ready(content, review, passage_slot=1)
    # Script may or may not pass length; L-KEY alone must not be the sole TTS blocker
    blockers = content.get("tts_blockers") or []
    assert not any(b.get("code") == "L-KEY" for b in blockers)
    if content.get("tts_ready"):
        assert "paper_blockers" in content


def test_cost_ledger_snapshot() -> None:
    reset()
    c = CallCounter()
    c.add_planner()
    c.add_generator(2)
    c.add_critic()
    record_run("listening", c)
    snap = snapshot()
    assert snap["modules"]["listening"]["llm_calls"] == 4
    assert snap["totals"]["runs"] == 1
    reset()
