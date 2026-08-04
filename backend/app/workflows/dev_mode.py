"""Dev-mode helpers — faster pipeline runs for local UI testing."""

from __future__ import annotations

from typing import Any


def dev_mode_enabled(state: dict[str, Any]) -> bool:
    """True when the run requested dev_mode (skip slow optional gates)."""
    return bool(state.get("dev_mode"))
