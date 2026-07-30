"""Verify tenant scoping on repositories."""

import uuid

import pytest
from app.infrastructure.db.errors import TenantScopeError
from app.infrastructure.db.repositories.base import TenantScopedRepository


def test_repository_without_org_id_raises() -> None:
    with pytest.raises(TenantScopeError):
        TenantScopedRepository(session=None, organization_id=None)  # type: ignore[arg-type]


def test_repository_with_org_id_succeeds() -> None:
    repo = TenantScopedRepository(session=None, organization_id=uuid.uuid4())  # type: ignore[arg-type]
    assert repo.organization_id is not None
