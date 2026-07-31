"""Threshold constants for Reading passage rules.

# ESTIMATE — tune against authentic material (see docs/execution/open-questions.md Q7).
"""

from __future__ import annotations

# Flesch-Kincaid grade level ranges by target IELTS band (inclusive min, exclusive max style).
FK_GRADE_BY_BAND: dict[float, tuple[float, float]] = {
    5.0: (8.0, 11.0),
    6.0: (10.0, 13.0),
    7.0: (12.0, 15.0),
    8.0: (14.0, 17.0),
    9.0: (15.0, 19.0),
}

# Max share of tokens below Zipf 4.0 (rarer vocabulary) by band — lower is stricter.
RARE_WORD_RATIO_MAX_BY_BAND: dict[float, float] = {
    5.0: 0.35,
    6.0: 0.30,
    7.0: 0.25,
    8.0: 0.20,
    9.0: 0.15,
}

# Minimum variance of sentence word counts (flat rhythm detector).
MIN_SENTENCE_LENGTH_VARIANCE = 4.0

# Heading-match sets need enough paragraphs for a bijection.
MIN_PARAGRAPHS_FOR_HEADING_MATCH = 6

# Zipf frequency floor — tokens below this count as "rare".
RARE_ZIPF_THRESHOLD = 4.0
