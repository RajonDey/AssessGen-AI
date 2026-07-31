"""Load and render versioned Reading prompt templates."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_ROOT = Path(__file__).resolve().parent
DEFAULT_VERSION = "v1"


@lru_cache(maxsize=64)
def load_prompt_template(*parts: str) -> str:
    path = PROMPTS_ROOT.joinpath(*parts)
    if not path.is_file():
        msg = f"Prompt template not found: {path}"
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8")


def render_prompt(template: str, **values: object) -> str:
    return template.format(**values)


def planner_prompt(*, variant: str, version: str = DEFAULT_VERSION) -> str:
    return load_prompt_template("planner", version, f"{variant}.md")


def passage_prompt(*, variant: str, version: str = DEFAULT_VERSION) -> str:
    return load_prompt_template("passage", version, f"{variant}.md")


def passage_adaptor_prompt(*, version: str = DEFAULT_VERSION) -> str:
    return load_prompt_template("passage", version, "adapt.md")


def question_prompt(*, item_type: str, version: str = DEFAULT_VERSION) -> str:
    return load_prompt_template("questions", version, f"{item_type}.md")


def answer_prompt(*, item_type: str, version: str = DEFAULT_VERSION) -> str:
    filename = "heading_match.md" if item_type == "heading_match" else "completion.md"
    return load_prompt_template("answers", version, filename)


def critic_prompt(*, version: str = DEFAULT_VERSION) -> str:
    return load_prompt_template("critic", version, "reading.md")


def reviser_prompt(*, version: str = DEFAULT_VERSION) -> str:
    return load_prompt_template("reviser", version, "reading.md")
