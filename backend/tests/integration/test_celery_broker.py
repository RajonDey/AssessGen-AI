"""Celery broker integration — requires Redis (docker compose --profile data)."""

from __future__ import annotations

import pytest
import redis
from app.config import get_settings
from app.infrastructure.queue.celery_app import celery_app
from app.infrastructure.queue.tasks.io import ping_io


@pytest.fixture(scope="module")
def redis_available() -> str:
    settings = get_settings()
    url = str(settings.redis_url)
    client = redis.from_url(url)  # type: ignore[no-untyped-call]
    try:
        client.ping()
    except redis.RedisError as exc:
        pytest.skip(f"Redis unavailable at {url}: {exc}")
    return url


def test_broker_accepts_io_task(redis_available: str) -> None:
    del redis_available
    previous_eager = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = False
    try:
        async_result = ping_io.apply_async(args=["broker"], queue="q.io")
        assert async_result.id
        assert async_result.backend is not None
    finally:
        celery_app.conf.task_always_eager = previous_eager
