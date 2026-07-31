"""Item bank endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_organization_id
from app.api.errors import ProblemDetail
from app.schemas.content import ItemDetail, ItemListResponse
from app.services.content_service import ContentService
from app.services.database import get_session

router = APIRouter(prefix="/items", tags=["items"])


async def get_content_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ContentService:
    return ContentService(session)


@router.get("", response_model=ItemListResponse)
async def list_items(
    organization_id: Annotated[UUID, Depends(get_organization_id)],
    service: Annotated[ContentService, Depends(get_content_service)],
) -> ItemListResponse:
    return await service.list_items(organization_id)


@router.get("/{item_id}", response_model=ItemDetail)
async def get_item(
    item_id: UUID,
    organization_id: Annotated[UUID, Depends(get_organization_id)],
    service: Annotated[ContentService, Depends(get_content_service)],
) -> ItemDetail:
    item = await service.get_item(item_id, organization_id=organization_id)
    if item is None:
        raise ProblemDetail(
            status=404,
            title="Item not found",
            detail=f"No item exists with id {item_id}.",
            type_suffix="item-not-found",
        )
    return item
