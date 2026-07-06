from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from polyalgo.api.deps import get_engine_dependency
from polyalgo.api.main import app
from polyalgo.db import init_db


def _make_test_client():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}, future=True
    )
    init_db(engine)
    app.dependency_overrides[get_engine_dependency] = lambda: engine
    client = TestClient(app)
    return client, engine


def test_health_returns_paper_mode_and_no_live_trading():
    client, _ = _make_test_client()
    response = client.get("/api/health")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] == "paper"
    assert body["live_trading_enabled"] is False
    assert body["database_connected"] is True


def test_health_reports_db_connected_true_for_working_db():
    client, _ = _make_test_client()
    response = client.get("/api/health")
    app.dependency_overrides.clear()

    assert response.json()["database_connected"] is True
