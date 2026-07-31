FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
COPY app ./app

RUN uv sync --frozen --no-dev

CMD ["uv", "run", "celery", "-A", "app.infrastructure.queue.celery_app", "worker", "--loglevel=info", "-Q", "q.generate,q.io,q.audio", "--concurrency=1"]
