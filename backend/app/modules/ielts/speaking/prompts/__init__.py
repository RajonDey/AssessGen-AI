"""Load and render versioned Speaking prompt templates."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_ROOT = Path(__file__).resolve().parent
DEFAULT_VERSION = "v1"


@lru_cache(maxsize=16)
def load_prompt_template(*parts: str) -> str:
    path = PROMPTS_ROOT.joinpath(*parts)
    if not path.is_file():
        msg = f"Prompt template not found: {path}"
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8")


def render_prompt(template: str, **values: object) -> str:
    return template.format(**values)


def part1_part2_prompt(*, version: str = DEFAULT_VERSION) -> str:
    return load_prompt_template("generator", version, "part1_part2.md")
