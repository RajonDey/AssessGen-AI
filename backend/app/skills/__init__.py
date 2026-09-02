"""Skill prompt loaders — versioned IELTS practice patterns from docs/question samples."""

from __future__ import annotations

from pathlib import Path

_SKILLS = Path(__file__).resolve().parent


def load_skill(module: str, role: str) -> str:
    """Load ``skills/<module>/<role>.md`` (generator or evaluator)."""
    path = _SKILLS / module / f"{role}.md"
    if not path.is_file():
        msg = f"Missing skill file: {path}"
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8").strip()
