"""Unit tests for reviewer payload parsing (no LLM)."""

from app.agents.reviewer import parse_review_payload


def test_valid_pass_payload() -> None:
    result = parse_review_payload(
        {
            "passed": True,
            "summary": "Looks good",
            "findings": [],
        }
    )
    assert result is not None
    assert result.passed is True
    assert result.findings == []


def test_must_finding_forces_fail() -> None:
    result = parse_review_payload(
        {
            "passed": True,
            "summary": "bad key",
            "findings": [
                {"severity": "must", "message": "Answer key wrong", "code": "KEY"},
            ],
        }
    )
    assert result is not None
    assert result.passed is False
    assert result.findings[0].severity == "must"


def test_empty_document_soft_passes() -> None:
    result = parse_review_payload(
        {"format": "text", "document": "", "type": "document"}
    )
    assert result is not None
    assert result.passed is True
    assert result.findings[0].code == "REV-SOFT"


def test_prose_document_soft_passes() -> None:
    result = parse_review_payload(
        {"format": "text", "document": "The paper is mostly fine.", "type": "document"}
    )
    assert result is not None
    assert result.passed is True
    assert result.findings[0].code == "REV-SOFT"


def test_missing_passed_defaults_from_findings() -> None:
    result = parse_review_payload(
        {
            "summary": "ok",
            "findings": [{"severity": "should", "message": "minor", "code": "M"}],
        }
    )
    assert result is not None
    assert result.passed is True


def test_findings_not_list_triggers_retry() -> None:
    assert parse_review_payload({"passed": True, "findings": "oops"}) is None
