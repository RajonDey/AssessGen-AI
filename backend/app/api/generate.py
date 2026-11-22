from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.pipeline import iter_generation_events, run_generation
from app.content.cost_ledger import snapshot as cost_snapshot, reset as cost_reset
from app.schemas.generation import GenerateRequest, GenerateResponse
from app.sessions import session_manager

log = logging.getLogger("assessgen")
router = APIRouter(prefix="/generate", tags=["generate"])


@router.get("/cost-stats")
async def generation_cost_stats() -> dict:
    """In-process LLM call totals (single-worker / dev cost dashboard)."""
    return cost_snapshot()


@router.post("/cost-stats/reset")
async def generation_cost_stats_reset() -> dict:
    cost_reset()
    return {"message": "cost stats reset", **cost_snapshot()}


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


@router.get("/writing/visual-briefs")
async def writing_visual_briefs_docs() -> dict:
    """Document the vendor handoff shape (POST body is the generated writing content)."""
    return {
        "usage": "POST /api/v1/generate/writing/visual-briefs with Writing content JSON",
        "fields": ["title", "question", "visual_brief", "task_type", "images"],
    }


@router.post("/writing/visual-briefs")
async def writing_visual_briefs(body: dict) -> dict:
    """Extract Task 1 visual briefs for an external image vendor."""
    from app.content.writing_brief import extract_writing_visual_briefs

    briefs = extract_writing_visual_briefs(body if isinstance(body, dict) else {})
    return {"count": len(briefs), "briefs": briefs}


@router.get("/listening/visual-briefs")
async def listening_visual_briefs_docs() -> dict:
    """Document Listening map/plan/diagram vendor handoff (POST body = listening content)."""
    return {
        "usage": "POST /api/v1/generate/listening/visual-briefs with Listening content JSON",
        "fields": [
            "partNumber",
            "groupRange",
            "type",
            "visual",
            "questions",
            "answer_key",
            "answer_evidence",
            "images",
            "image_status",
            "audio_cue",
        ],
        "notes": (
            "images[] may be empty (pending_vendor). "
            "Synthesize WAV from the part script via POST /api/v1/listening/synthesize."
        ),
    }


@router.post("/listening/visual-briefs")
async def listening_visual_briefs(body: dict) -> dict:
    """Extract map/plan/diagram packs for an external image vendor (+ script cues)."""
    from app.content.listening_brief import extract_listening_visual_briefs

    briefs = extract_listening_visual_briefs(body if isinstance(body, dict) else {})
    return {"count": len(briefs), "briefs": briefs}


@router.post("/session/create")
async def create_session(body: dict) -> dict:
    """Create a new multi-part generation session.

    Body fields: module, topic, target_band?, total_parts?, topics?, type_plan?,
    topic_t1?, topic_t2?, task1_kind?, task2_kind?
    """
    module = str(body.get("module") or "")
    topic = str(body.get("topic") or "")
    if module not in {"reading", "writing", "listening"}:
        raise HTTPException(status_code=400, detail="module must be reading|writing|listening")
    if len(topic.strip()) < 2:
        raise HTTPException(status_code=400, detail="topic is required")
    target_band = float(body.get("target_band") or 6.5)
    caps = {"reading": 3, "writing": 2, "listening": 4}
    total_parts = int(body.get("total_parts") or caps[module])
    topics = body.get("topics")
    type_plan = body.get("type_plan")
    session = session_manager.create_session(
        module=module,
        topic=topic,
        target_band=target_band,
        total_parts=total_parts,
        topics=list(topics) if isinstance(topics, list) else None,
        type_plan=list(type_plan) if isinstance(type_plan, list) else None,
        topic_t1=body.get("topic_t1"),
        topic_t2=body.get("topic_t2"),
        task1_kind=body.get("task1_kind"),
        task2_kind=body.get("task2_kind"),
    )
    return {
        "session_id": session.session_id,
        "module": session.module,
        "topic": session.topic,
        "topics": session.topics,
        "type_plan": session.type_plan,
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
        "topics": session.topics,
        "type_plan": session.type_plan,
        "topic_t1": session.topic_t1,
        "topic_t2": session.topic_t2,
        "task1_kind": session.task1_kind,
        "task2_kind": session.task2_kind,
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
