"""LangGraph PostgresSaver setup."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import Settings, get_settings

_setup_complete = False


def checkpoint_conn_string(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + database_url.removeprefix("postgresql+psycopg://")
    return database_url


async def ensure_checkpoint_schema(checkpointer: AsyncPostgresSaver) -> None:
    global _setup_complete
    if _setup_complete:
        return
    await checkpointer.setup()
    _setup_complete = True


def reset_checkpoint_schema_flag() -> None:
    """Reset setup flag — for tests only."""
    global _setup_complete
    _setup_complete = False


@asynccontextmanager
async def postgres_checkpointer(
    settings: Settings | None = None,
) -> AsyncIterator[AsyncPostgresSaver]:
    cfg = settings or get_settings()
    conn_string = checkpoint_conn_string(str(cfg.database_url))
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await ensure_checkpoint_schema(checkpointer)
        yield checkpointer
