from __future__ import annotations

from sqlalchemy.engine import Engine

from polyalgo.db import get_engine as _get_engine


def get_engine_dependency() -> Engine:
    """FastAPI dependency wrapping polyalgo.db.get_engine.

    Exists as its own function (rather than routes importing get_engine
    directly) so tests can override it via
    `app.dependency_overrides[get_engine_dependency] = lambda: test_engine`
    to point routes at an isolated in-memory database.
    """
    return _get_engine()
