"""Unit tests for structural rules and skills."""

from pathlib import Path

from app.rules.structure import evaluate_structure
from app.skills import load_skill

ROOT = Path(__file__).resolve().parents[2]


def test_skills_exist() -> None:
    for module in ("reading", "writing", "listening"):
        skill = load_skill(module, "generator").lower()
        assert "markdown" in skill or "json" in skill
        assert load_skill(module, "evaluator")


def test_markdown_document_passes_structure() -> None:
    content = {
        "format": "markdown",
        "type": "document",
        "document": "# Reading\n\n" + ("Passage text. " * 20),
    }
    report = evaluate_structure("reading", content)
    assert report.passed


def test_writing_sample_passes_structure() -> None:
    import json

    content = json.loads((ROOT / "docs/question/writing-01.json").read_text(encoding="utf-8"))
    report = evaluate_structure("writing", content)
    assert report.passed, [f.message for f in report.findings if f.severity == "must"]


def test_reading_sample_passes_structure() -> None:
    import json

    content = json.loads((ROOT / "docs/question/reading-01.json").read_text(encoding="utf-8"))
    report = evaluate_structure("reading", content)
    assert report.passed, [f.message for f in report.findings if f.severity == "must"]


def test_planted_writing_missing_task1_fails() -> None:
    import json

    raw = json.loads(
        (ROOT / "evals/fixtures/planted/writing_missing_task1.json").read_text(encoding="utf-8")
    )
    report = evaluate_structure("writing", raw["content"])
    assert not report.passed
