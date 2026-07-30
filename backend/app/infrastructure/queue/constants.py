"""Celery queue names."""

GENERATE_QUEUE = "q.generate"
IO_QUEUE = "q.io"
AUDIO_QUEUE = "q.audio"

ALL_QUEUES = (GENERATE_QUEUE, IO_QUEUE, AUDIO_QUEUE)
