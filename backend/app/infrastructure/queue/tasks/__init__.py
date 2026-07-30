"""Celery task registration."""

from app.infrastructure.queue.tasks import audio, io

__all__ = ["audio", "io"]
