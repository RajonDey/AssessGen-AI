"""Band threshold lookup helpers."""

from __future__ import annotations

from collections.abc import Mapping

from app.modules.ielts.reading.thresholds import FK_GRADE_BY_BAND, RARE_WORD_RATIO_MAX_BY_BAND


def nearest_band_key(target_band: float, mapping: Mapping[float, object]) -> float:
    keys = sorted(mapping)
    selected = keys[0]
    for key in keys:
        if target_band >= key - 0.25:
            selected = key
    return selected


def fk_grade_range(target_band: float) -> tuple[float, float]:
    key = nearest_band_key(target_band, FK_GRADE_BY_BAND)
    return FK_GRADE_BY_BAND[key]


def rare_word_ratio_max(target_band: float) -> float:
    key = nearest_band_key(target_band, RARE_WORD_RATIO_MAX_BY_BAND)
    return RARE_WORD_RATIO_MAX_BY_BAND[key]
