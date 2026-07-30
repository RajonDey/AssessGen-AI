"""Dependency wiring — composition root for services and infrastructure."""

from app.config import Settings, get_settings


class Container:
    """Holds shared dependencies. Expanded as layers are implemented."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()


_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container() -> None:
    """Reset the singleton — for tests only."""
    global _container
    _container = None
