"""Request/response schemas for generation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ModuleName = Literal["reading", "writing", "listening"]
WritingType = Literal[
    "opinion",
    "discussion",
    "problem_solution",
    "advantages_disadvantages",
    "two_part",
]


class GenerateRequest(BaseModel):
    module: ModuleName
    topic: str = Field(min_length=2, max_length=200)
    target_band: float = Field(default=6.5, ge=4.0, le=9.0)
    question_count: int = Field(default=13, ge=1, le=40)
    writing_type: WritingType = "opinion"
    """How many Reading sections / Writing parts / Listening parts to generate."""
    part_count: int = Field(default=1, ge=1, le=4)
    listening_section: int = Field(default=1, ge=1, le=4)
    full_paper: bool = False
    
    # Multi-part linking support
    session_id: str | None = Field(default=None, description="Session ID for linking multi-part generations")
    previous_content: dict[str, Any] | None = Field(default=None, description="Content from previous part(s) for context")
    current_part: int = Field(default=1, ge=1, le=4, description="Current part number in sequence (1-based)")
    total_parts: int = Field(default=1, ge=1, le=4, description="Total parts to generate in this session")

    @model_validator(mode="after")
    def _clamp_parts(self) -> GenerateRequest:
        caps = {"reading": 3, "writing": 2, "listening": 4}
        cap = caps[self.module]
        if self.full_paper:
            object.__setattr__(self, "part_count", cap)
            object.__setattr__(self, "total_parts", cap)
        elif self.part_count > cap:
            object.__setattr__(self, "part_count", cap)
        # Multi-section Reading / Listening: total_parts tracks the planned paper size
        if (
            self.module in {"reading", "listening"}
            and self.part_count > 1
            and self.total_parts < self.part_count
        ):
            object.__setattr__(self, "total_parts", self.part_count)
        return self


class ReviewFinding(BaseModel):
    severity: Literal["must", "should", "info"] = "should"
    message: str
    code: str | None = None


class ReviewResult(BaseModel):
    passed: bool
    findings: list[ReviewFinding] = Field(default_factory=list)
    summary: str = ""
    source: Literal["rules", "llm", "combined"] = "combined"


class GenerateResponse(BaseModel):
    module: ModuleName
    topic: str
    target_band: float
    part_count: int = 1
    content: dict[str, Any]
    review: ReviewResult
    revision_attempts: int
    provider: str
    generator_model: str
    reviewer_model: str
    reasoning: str = ""
    plan_steps: list[str] = Field(default_factory=list)
    session_id: str | None = None
    parts_linked: int = Field(
        default=1,
        description="How many sections/parts were generated and linked in this run",
    )


class ProgressEvent(BaseModel):
    """SSE payload for live generation UI."""

    stage: Literal[
        "planning",
        "reasoning",
        "generating",
        "rules",
        "reviewing",
        "revising",
        "done",
        "error",
    ]
    message: str
    reasoning: str | None = None
    step: str | None = None
    result: GenerateResponse | None = None
