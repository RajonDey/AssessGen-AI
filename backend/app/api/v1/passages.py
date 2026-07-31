"""Passage bank endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_organization_id
from app.api.errors import ProblemDetail
from app.schemas.content import PassageDetail, PassageListResponse
from app.services.content_service import ContentService
from app.services.database import get_session

router = APIRouter(prefix="/passages", tags=["passages"])


async def get_content_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ContentService:
    return ContentService(session)


@router.get("", response_model=PassageListResponse)
async def list_passages(
    organization_id: Annotated[UUID, Depends(get_organization_id)],
    service: Annotated[ContentService, Depends(get_content_service)],
) -> PassageListResponse:
    return await service.list_passages(organization_id)


@router.get("/{passage_id}", response_model=PassageDetail)
async def get_passage(
    passage_id: UUID,
    organization_id: Annotated[UUID, Depends(get_organization_id)],
    service: Annotated[ContentService, Depends(get_content_service)],
) -> PassageDetail:
    passage = await service.get_passage(passage_id, organization_id=organization_id)
    if passage is None:
        raise ProblemDetail(
            status=404,
            title="Passage not found",
            detail=f"No passage exists with id {passage_id}.",
            type_suffix="passage-not-found",
        )
    return passage
