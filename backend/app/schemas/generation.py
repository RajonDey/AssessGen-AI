"""Request/response schemas for generation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ModuleName = Literal["reading", "writing", "listening"]
QualityMode = Literal["draft", "standard", "publish"]
WritingType = Literal[
    "opinion",
    "discussion",
    "problem_solution",
    "advantages_disadvantages",
    "two_part",
]
Task1Kind = Literal[
    "line_graph",
    "bar_chart",
    "pie_chart",
    "table",
    "process",
    "map",
    "mixed",
    "letter_formal",
    "letter_semi_formal",
    "letter_informal",
]


class GenerateRequest(BaseModel):
    module: ModuleName
    topic: str = Field(
        min_length=2,
        max_length=200,
        description="Primary topic (Part 1 / display). Prefer topics[] for multi-part papers.",
    )
    target_band: float = Field(default=6.5, ge=4.0, le=9.0)
    question_count: int = Field(default=13, ge=1, le=40)
    writing_type: WritingType = "opinion"
    """How many Reading sections / Writing parts / Listening parts to generate."""
    part_count: int = Field(default=1, ge=1, le=4)
    listening_section: int = Field(default=1, ge=1, le=4)
    full_paper: bool = False
    quality_mode: QualityMode = Field(
        default="standard",
        description=(
            "draft=generate+rules only; standard=+critic when rules pass; "
            "publish=+originality hard-check when available"
        ),
    )

    # Per-part paper spec (BC-style: independent topics; interlocking item types)
    topics: list[str] | None = Field(
        default=None,
        description=(
            "One independent topic per part. Length must equal part_count when set. "
            "Listening: 4, Reading: 3, Writing: use topic_t1/topic_t2 (or topics[0]/topics[1])."
        ),
    )
    type_plan: list[list[str]] | None = Field(
        default=None,
        description=(
            "Per-part question-type lists for Reading/Listening. "
            "Listening Parts 1–3: 2–3 types; Part 4: exactly one notes type. "
            "Reading: 2–3 types per passage, diversified across the paper. "
            "Omitted → BC-typical defaults."
        ),
    )
    topic_t1: str | None = Field(
        default=None,
        max_length=200,
        description="Writing Task 1 topic (independent of Task 2).",
    )
    topic_t2: str | None = Field(
        default=None,
        max_length=200,
        description="Writing Task 2 topic (independent of Task 1).",
    )
    task1_kind: Task1Kind | None = Field(
        default=None,
        description="Writing Task 1 visual/letter kind (default bar_chart).",
    )
    task2_kind: WritingType | None = Field(
        default=None,
        description="Writing Task 2 essay kind; defaults to writing_type.",
    )

    # Multi-part linking support
    session_id: str | None = Field(
        default=None, description="Session ID for linking multi-part generations"
    )
    previous_content: dict[str, Any] | None = Field(
        default=None, description="Content from previous part(s) for context"
    )
    current_part: int = Field(
        default=1, ge=1, le=4, description="Current part number in sequence (1-based)"
    )
    total_parts: int = Field(
        default=1, ge=1, le=4, description="Total parts to generate in this session"
    )

    @model_validator(mode="after")
    def _clamp_parts_and_spec(self) -> GenerateRequest:
        from app.content.paper_spec import (
            default_task1_kind,
            resolve_topics,
            resolve_type_plan,
            validate_paper_spec,
        )

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

        n = self.part_count
        # Autofill type_plan defaults when omitted (Reading/Listening)
        if self.module in {"reading", "listening"} and self.type_plan is None and n >= 1:
            if self.module == "listening" and n == 1:
                from app.content.paper_spec import default_listening_type_plan

                full = default_listening_type_plan()
                sec = max(1, min(4, self.listening_section))
                object.__setattr__(self, "type_plan", [list(full[sec - 1])])
            else:
                object.__setattr__(
                    self,
                    "type_plan",
                    resolve_type_plan(module=self.module, type_plan=None, part_count=n),
                )

        # Autofill topics from primary topic when multi-part omitted (compat)
        if self.topics is None and n >= 1:
            object.__setattr__(
                self,
                "topics",
                resolve_topics(
                    module=self.module,
                    topic=self.topic,
                    topics=None,
                    part_count=n,
                    topic_t1=self.topic_t1,
                    topic_t2=self.topic_t2,
                ),
            )

        if self.module == "writing":
            if self.task1_kind is None:
                object.__setattr__(self, "task1_kind", default_task1_kind())
            if self.task2_kind is None:
                object.__setattr__(self, "task2_kind", self.writing_type)
            else:
                object.__setattr__(self, "writing_type", self.task2_kind)
            if self.topic_t1 is None and self.topics:
                object.__setattr__(self, "topic_t1", self.topics[0])
            if self.topic_t2 is None and self.topics and len(self.topics) > 1:
                object.__setattr__(self, "topic_t2", self.topics[1])
            elif self.topic_t2 is None and n > 1:
                object.__setattr__(self, "topic_t2", self.topic)

        # Hard-fail invalid explicit specs (after autofill, topics/type_plan are set)
        findings = validate_paper_spec(
            module=self.module,
            part_count=n,
            topics=self.topics,
            type_plan=self.type_plan if self.module != "writing" else None,
            topic=self.topic,
            topic_t1=self.topic_t1,
            topic_t2=self.topic_t2,
            task1_kind=self.task1_kind,
            task2_kind=self.task2_kind,
            writing_type=self.writing_type,
            listening_section=self.listening_section,
            total_parts=self.total_parts,
            current_part=self.current_part,
        )
        musts = [f for f in findings if f.severity == "must"]
        if musts:
            raise ValueError("; ".join(f.message for f in musts))

        return self

    def topic_for_part(self, part_number: int) -> str:
        from app.content.paper_spec import part_topic, resolve_topics

        topics = self.topics or resolve_topics(
            module=self.module,
            topic=self.topic,
            topics=self.topics,
            part_count=max(self.part_count, self.total_parts, part_number),
            topic_t1=self.topic_t1,
            topic_t2=self.topic_t2,
        )
        return part_topic(topics, part_number, self.topic)

    def types_for_part(self, part_number: int) -> list[str]:
        from app.content.paper_spec import part_types, resolve_type_plan

        plan = self.type_plan or resolve_type_plan(
            module=self.module,
            type_plan=None,
            part_count=max(self.part_count, self.total_parts, part_number),
        )
        return part_types(plan, part_number)


class ReviewFinding(BaseModel):
    severity: Literal["must", "should", "info"] = "should"
    message: str
    code: str | None = None


class ReviewResult(BaseModel):
    passed: bool
    findings: list[ReviewFinding] = Field(default_factory=list)
    summary: str = ""
    source: Literal["rules", "llm", "combined"] = "combined"


class CostStats(BaseModel):
    """Per-run LLM call accounting for cost control."""

    llm_calls: int = 0
    planner_calls: int = 0
    generator_calls: int = 0
    critic_calls: int = 0
    quality_mode: QualityMode = "standard"
    prompt_hash: str | None = None


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
    quality_mode: QualityMode = "standard"
    cost: CostStats = Field(default_factory=CostStats)
    topics: list[str] | None = None
    type_plan: list[list[str]] | None = None
    topic_t1: str | None = None
    topic_t2: str | None = None
    task1_kind: str | None = None
    task2_kind: str | None = None


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
