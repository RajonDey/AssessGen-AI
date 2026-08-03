"""Load and render versioned Listening prompt templates."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_ROOT = Path(__file__).resolve().parent
DEFAULT_VERSION = "v1"


@lru_cache(maxsize=32)
def load_prompt_template(*parts: str) -> str:
    path = PROMPTS_ROOT.joinpath(*parts)
    if not path.is_file():
        msg = f"Prompt template not found: {path}"
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8")


def render_prompt(template: str, **values: object) -> str:
    return template.format(**values)


def planner_prompt(*, version: str = DEFAULT_VERSION) -> str:
    return load_prompt_template("planner", version, "section.md")


def script_prompt(*, section: int, version: str = DEFAULT_VERSION) -> str:
    name = "section_1.md" if section == 1 else "section_2.md"
    return load_prompt_template("script", version, name)
