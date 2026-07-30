"""Tenant-scoped repository base."""

import uuid
from typing import Any

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.errors import TenantScopeError


class TenantScopedRepository:
    """All content queries require an organization_id scope."""

    def __init__(self, session: AsyncSession, organization_id: uuid.UUID | None) -> None:
        if organization_id is None:
            raise TenantScopeError("organization_id is required for all content repository queries")
        self.session = session
        self.organization_id = organization_id

    def scope(self, stmt: Select[Any], column: Any) -> Select[Any]:
        return stmt.where(column == self.organization_id)
