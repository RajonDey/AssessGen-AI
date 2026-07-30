def test_app_imports() -> None:
    import app

    assert app.__version__ == "0.1.0"


def test_create_app_has_health_route() -> None:
    from app.main import create_app

    app = create_app()
    paths = app.openapi()["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/me" in paths


def test_domain_enums_are_strings() -> None:
    from app.domain.enums import ItemStatus, Module, Severity

    assert Module.READING.value == "reading"
    assert ItemStatus.DRAFT.value == "draft"
    assert Severity.MUST.value == "must"
