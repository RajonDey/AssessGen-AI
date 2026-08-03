"""IELTS Listening format bounds — Phase 1C (Sections 1–2 only)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListeningSpec:
    phase_1c_sections: tuple[int, ...] = (1, 2)
    section_1_min_turns: int = 12
    section_2_min_turns: int = 8
    section_1_speaker_count: int = 2
    section_2_speaker_count: int = 1
