"""FastAPI application — lightweight IELTS generation API."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.generate import router as generate_router
from app.api.listening_audio import router as listening_audio_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )
    app = FastAPI(
        title=settings.app_name,
        version="0.3.0",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "provider": settings.llm_provider,
        }

    app.include_router(generate_router, prefix="/api/v1")
    app.include_router(listening_audio_router, prefix="/api/v1")
    return app


app = create_app()
