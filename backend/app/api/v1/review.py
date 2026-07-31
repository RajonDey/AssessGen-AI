"""Review queue endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_organization_id
from app.schemas.review import ReviewQueueResponse
from app.services.database import get_session
from app.services.review_service import ReviewService

router = APIRouter(prefix="/review", tags=["review"])


async def get_review_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReviewService:
    return ReviewService(session)


@router.get("/queue", response_model=ReviewQueueResponse)
async def list_review_queue(
    organization_id: Annotated[UUID, Depends(get_organization_id)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> ReviewQueueResponse:
    return await service.list_queue(organization_id)
