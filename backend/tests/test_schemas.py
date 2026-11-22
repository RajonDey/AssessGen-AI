"""Smoke tests for schemas (no LLM calls)."""

from app.schemas.generation import GenerateRequest


def test_generate_request_defaults() -> None:
    req = GenerateRequest(module="reading", topic="climate")
    assert req.target_band == 6.5
    assert req.question_count == 13
    assert req.part_count == 1
    assert req.full_paper is False


def test_part_count_clamped_for_writing() -> None:
    req = GenerateRequest(module="writing", topic="air travel", part_count=4)
    assert req.part_count == 2
