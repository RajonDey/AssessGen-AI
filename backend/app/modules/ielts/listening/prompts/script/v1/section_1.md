Write an IELTS Listening Section 1 dialogue script as JSON.

Context: {context}
Topic angle: {topic}
Target band: {target_band}
Accent: {accent}
Minimum turns: {min_turns}
Speakers: exactly 2 (receptionist/clerk + customer/enquirer)

Requirements:
- Natural spoken register with contractions and questions (not essay prose)
- Include hesitations (um, uh) and at least one self-correction ("Tuesday — sorry, Wednesday")
- Spell out at least one proper noun letter-by-letter when needed
- Speak numbers and dates naturally (not raw long digit strings like 07941234567)
- Spread factual details across the conversation timeline
- Answers for completion items must appear verbatim in turn text as spoken

Return JSON matching this shape:

{json_example}

Return only valid JSON. Offsets (start_char/end_char) may be placeholders; they will be normalized.
