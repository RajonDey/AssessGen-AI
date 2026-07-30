"""FastAPI middleware for request correlation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars

from app.infrastructure.observability.logging import (
    clear_log_context,
    get_logger,
    new_request_id,
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-Id") or new_request_id()
        bind_contextvars(request_id=request_id)
        log = get_logger("app.api")
        log.info(
            "http.request.started",
            method=request.method,
            path=request.url.path,
        )
        try:
            response = await call_next(request)
        except Exception:
            log.exception("http.request.failed", method=request.method, path=request.url.path)
            raise
        else:
            log.info(
                "http.request.completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
            )
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            clear_log_context()
