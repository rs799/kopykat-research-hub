import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from polyalgo.api.deps import get_engine_dependency
from polyalgo.api.main import app
from polyalgo.db import init_db


@pytest.fixture()
def client_and_engine():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}, future=True
    )
    init_db(engine)
    app.dependency_overrides[get_engine_dependency] = lambda: engine
    yield TestClient(app), engine
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Niches - honestly empty, not implemented yet
# ---------------------------------------------------------------------------


def test_list_niches_is_empty_not_fabricated(client_and_engine):
    client, _ = client_and_engine
    response = client.get("/api/niches")
    assert response.status_code == 200
    assert response.json() == []


def test_wallet_discovery_for_niche_is_empty(client_and_engine):
    client, _ = client_and_engine
    response = client.get("/api/niches/crypto/wallet-discovery")
    assert response.status_code == 200
    assert response.json() == []


def test_wallet_rankings_for_niche_is_empty(client_and_engine):
    client, _ = client_and_engine
    response = client.get("/api/niches/crypto/wallet-rankings")
    assert response.status_code == 200
    assert response.json() == []


def test_niche_endpoints_accept_arbitrary_niche_key(client_and_engine):
    """Since niche classification doesn't exist yet, any niche key should
    still return a clean empty response rather than erroring."""
    client, _ = client_and_engine
    response = client.get("/api/niches/totally-made-up-niche/wallet-discovery")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# Consensus alerts - honestly empty / 404, consensus engine not implemented
# ---------------------------------------------------------------------------


def test_list_consensus_alerts_is_empty(client_and_engine):
    client, _ = client_and_engine
    response = client.get("/api/consensus-alerts")
    assert response.status_code == 200
    assert response.json() == []


def test_get_alert_by_id_is_404_not_fabricated(client_and_engine):
    client, _ = client_and_engine
    response = client.get("/api/alerts/AL-1000")
    assert response.status_code == 404
    assert "not implemented" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Backtests - honestly empty, backtest engine not implemented
# ---------------------------------------------------------------------------


def test_list_backtests_is_empty(client_and_engine):
    client, _ = client_and_engine
    response = client.get("/api/backtests")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# Data health - real DB-backed
# ---------------------------------------------------------------------------


def test_data_health_on_empty_db(client_and_engine):
    client, _ = client_and_engine
    response = client.get("/api/data-health")
    assert response.status_code == 200
    body = response.json()
    assert body["rawRows"] == 0
    assert body["lifecycleEvents"] == 0
    assert body["unresolvedIssues"] == 0
    assert body["warnings"] == []
    assert all(e["status"] == "no_data" for e in body["endpoints"])


def test_data_health_reflects_parser_warnings(client_and_engine):
    client, engine = client_and_engine
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO wallet_activity_raw (wallet_address, activity_type, parsed_ok, parse_warning) "
                "VALUES ('0xabc', 'MERGE', 0, 'missing timestamp')"
            )
        )

    response = client.get("/api/data-health")
    body = response.json()
    assert body["unresolvedIssues"] == 1
    assert len(body["warnings"]) == 1
    assert body["warnings"][0]["wallet"] == "0xabc"
    assert body["warnings"][0]["message"] == "missing timestamp"
    # severity is a documented placeholder, not a real classification yet
    assert body["warnings"][0]["severity"] == "low"


def test_data_health_endpoint_shows_ok_when_data_present(client_and_engine):
    client, engine = client_and_engine
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO wallet_trades (wallet, ts, market_id, condition_id, token_id, outcome, side, price, size, usdc_size) "
                "VALUES ('0xabc', CURRENT_TIMESTAMP, 'm1', 'c1', 'tok1', 'YES', 'BUY', 0.4, 100, 40)"
            )
        )

    response = client.get("/api/data-health")
    endpoints = {e["name"]: e["status"] for e in response.json()["endpoints"]}
    assert endpoints["wallet_trades"] == "ok"
