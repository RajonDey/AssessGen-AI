"""Infrastructure-level database errors."""


class TenantScopeError(Exception):
    """Raised when a repository query lacks organization_id scoping."""
