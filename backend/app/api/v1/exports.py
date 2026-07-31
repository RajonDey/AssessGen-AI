"""Content export endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_organization_id
from app.api.errors import ProblemDetail
from app.domain.entities.user import AuthenticatedUser
from app.schemas.export import ReadingExportRequest, ReadingExportResponse
from app.services.database import get_session
from app.services.export_service import ExportError, ExportService

router = APIRouter(prefix="/exports", tags=["exports"])


async def get_export_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ExportService:
    return ExportService(session)


@router.post("/reading", response_model=ReadingExportResponse)
async def export_reading_run(
    body: ReadingExportRequest,
    _user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    organization_id: Annotated[UUID, Depends(get_organization_id)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> ReadingExportResponse:
    try:
        bundle = await service.export_reading_run(
            run_id=body.run_id,
            organization_id=organization_id,
            publish=body.publish,
        )
    except ExportError as exc:
        raise ProblemDetail(
            status=409,
            title="Export failed",
            detail=str(exc),
            type_suffix="export-failed",
        ) from exc

    return ReadingExportResponse.model_validate(bundle)
