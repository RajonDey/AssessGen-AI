"""Unit tests for dev-mode graph routing helpers."""

from app.workflows.dev_mode import dev_mode_enabled


def test_dev_mode_enabled_false_by_default() -> None:
    assert dev_mode_enabled({}) is False
    assert dev_mode_enabled({"dev_mode": False}) is False


def test_dev_mode_enabled_true() -> None:
    assert dev_mode_enabled({"dev_mode": True}) is True
