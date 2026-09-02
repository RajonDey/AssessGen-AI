from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.pipeline import iter_generation_events, run_generation
from app.schemas.generation import GenerateRequest, GenerateResponse
from app.sessions import session_manager

log = logging.getLogger("assessgen")
router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("", response_model=GenerateResponse)
async def generate(body: GenerateRequest) -> GenerateResponse:
    try:
        return await run_generation(body)
    except Exception as exc:  # noqa: BLE001
        log.exception("generation.failed module=%s", body.module)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/stream")
async def generate_stream(body: GenerateRequest) -> StreamingResponse:
    """NDJSON stream of ProgressEvent objects (one JSON object per line)."""

    async def _ndjson():
        async for event in iter_generation_events(body):
            yield event.model_dump_json() + "\n"

    return StreamingResponse(
        _ndjson(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# Session management endpoints

@router.post("/session/create")
async def create_session(
    module: str,
    topic: str,
    target_band: float = 6.5,
    total_parts: int = 3,
) -> dict:
    """Create a new multi-part generation session."""
    session = session_manager.create_session(
        module=module,
        topic=topic,
        target_band=target_band,
        total_parts=total_parts,
    )
    return {
        "session_id": session.session_id,
        "module": session.module,
        "topic": session.topic,
        "total_parts": session.total_parts,
        "message": f"Session created. Use session_id '{session.session_id}' for subsequent parts.",
    }


@router.get("/session/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get session state and generated parts."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session.session_id,
        "module": session.module,
        "topic": session.topic,
        "target_band": session.target_band,
        "current_part": session.current_part,
        "total_parts": session.total_parts,
        "parts_generated": len(session.parts),
        "parts": session.parts,
        "summary": session.get_summary(),
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str) -> dict:
    """Delete a generation session."""
    if session_manager.delete_session(session_id):
        return {"message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/sessions")
async def list_sessions() -> dict:
    """List all active sessions."""
    return {"sessions": session_manager.list_sessions()}
