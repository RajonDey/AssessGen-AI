"""RFC 9457 Problem Details error handling."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_JSON = "application/problem+json"
ERROR_BASE = "https://assessgen.ai/errors"


class ProblemDetail(Exception):
    def __init__(
        self,
        *,
        status: int,
        title: str,
        detail: str,
        type_suffix: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.status = status
        self.title = title
        self.detail = detail
        self.type_suffix = type_suffix
        self.extra = extra or {}


class UnauthorizedProblem(ProblemDetail):
    def __init__(self, detail: str = "Authentication required.") -> None:
        super().__init__(
            status=401,
            title="Unauthorized",
            detail=detail,
            type_suffix="unauthorized",
        )


class ForbiddenProblem(ProblemDetail):
    def __init__(self, detail: str = "Insufficient permissions.") -> None:
        super().__init__(
            status=403,
            title="Forbidden",
            detail=detail,
            type_suffix="forbidden",
        )


class InvalidCredentialsProblem(ProblemDetail):
    def __init__(self) -> None:
        super().__init__(
            status=401,
            title="Invalid credentials",
            detail="Email or password is incorrect.",
            type_suffix="invalid-credentials",
        )


def _problem_body(request: Request, exc: ProblemDetail) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": f"{ERROR_BASE}/{exc.type_suffix}",
        "title": exc.title,
        "status": exc.status,
        "detail": exc.detail,
        "instance": request.url.path,
    }
    body.update(exc.extra)
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemDetail)
    async def problem_detail_handler(request: Request, exc: ProblemDetail) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=_problem_body(request, exc),
            media_type=PROBLEM_JSON,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        problem = ProblemDetail(
            status=exc.status_code,
            title="Request failed",
            detail=str(exc.detail),
            type_suffix="http-error",
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_problem_body(request, problem),
            media_type=PROBLEM_JSON,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        problem = ProblemDetail(
            status=422,
            title="Validation error",
            detail="Request body or parameters failed validation.",
            type_suffix="validation-error",
            extra={"errors": exc.errors()},
        )
        return JSONResponse(
            status_code=422,
            content=_problem_body(request, problem),
            media_type=PROBLEM_JSON,
        )
