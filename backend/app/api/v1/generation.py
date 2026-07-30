"""Generation run endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_organization_id
from app.api.errors import ProblemDetail
from app.domain.entities.user import AuthenticatedUser
from app.infrastructure.observability.logging import bind_run_context, get_logger
from app.schemas.generation import CreateGenerationRunRequest, GenerationRunResponse
from app.services.database import get_session
from app.services.generation_service import DuplicateIdempotencyKeyError, GenerationService

router = APIRouter(prefix="/generation", tags=["generation"])


async def get_generation_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GenerationService:
    return GenerationService(session)


@router.post(
    "/runs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenerationRunResponse,
)
async def create_generation_run(
    body: CreateGenerationRunRequest,
    response: Response,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> GenerationRunResponse:
    if not idempotency_key:
        raise ProblemDetail(
            status=400,
            title="Missing idempotency key",
            detail="Idempotency-Key header is required for generation requests.",
            type_suffix="missing-idempotency-key",
        )

    try:
        run = await service.create_smoke_run(
            organization_id=organization_id,
            requested_by=user.id,
            idempotency_key=idempotency_key,
            body=body,
        )
    except DuplicateIdempotencyKeyError as exc:
        raise ProblemDetail(
            status=409,
            title="Idempotency key conflict",
            detail="The idempotency key was reused with a different request body.",
            type_suffix="idempotency-conflict",
        ) from exc

    bind_run_context(str(run.id))
    get_logger("app.generation").info("run.created", module=run.module, status=run.status)

    response.headers["Location"] = f"/api/v1/generation/runs/{run.id}"
    return GenerationService.to_response(run)


@router.get("/runs/{run_id}", response_model=GenerationRunResponse)
async def get_generation_run(
    run_id: UUID,
    organization_id: Annotated[UUID, Depends(get_organization_id)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> GenerationRunResponse:
    run = await service.runs.get_by_id(run_id, organization_id=organization_id)
    if run is None:
        raise ProblemDetail(
            status=404,
            title="Run not found",
            detail=f"No generation run exists with id {run_id}.",
            type_suffix="run-not-found",
        )
    return GenerationService.to_response(run)
