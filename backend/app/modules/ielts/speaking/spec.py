"""IELTS Speaking format bounds — Phase 1C (Part 1 + Part 2)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpeakingSpec:
    part1_topic_count: int = 3
    part1_questions_min: int = 3
    part1_questions_max: int = 4
    part2_bullet_count: int = 3
