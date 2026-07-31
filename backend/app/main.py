"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.middleware import RequestLoggingMiddleware
from app.api.v1.auth import router as auth_router
from app.api.v1.exports import router as exports_router
from app.api.v1.generation import router as generation_router
from app.api.v1.items import router as items_router
from app.api.v1.passages import router as passages_router
from app.api.v1.quality import router as quality_router
from app.api.v1.review import router as review_router
from app.config import get_settings
from app.container import get_container
from app.infrastructure.observability.logging import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging(get_settings())
    get_container()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    @app.get("/api/v1/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(generation_router, prefix="/api/v1")
    app.include_router(review_router, prefix="/api/v1")
    app.include_router(passages_router, prefix="/api/v1")
    app.include_router(items_router, prefix="/api/v1")
    app.include_router(quality_router, prefix="/api/v1")
    app.include_router(exports_router, prefix="/api/v1")

    return app


app = create_app()
