from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from polyalgo.api.deps import get_engine_dependency
from polyalgo.api.main import app
from polyalgo.db import init_db
from polyalgo.ingest.tracked_wallets import add_wallet
from polyalgo.scoring.wallets import score_all_wallets


@pytest.fixture()
def client_and_engine():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}, future=True
    )
    init_db(engine)
    app.dependency_overrides[get_engine_dependency] = lambda: engine
    yield TestClient(app), engine
    app.dependency_overrides.clear()


def test_list_wallets_empty(client_and_engine):
    client, _ = client_and_engine
    response = client.get("/api/wallets")
    assert response.status_code == 200
    assert response.json() == []


def test_add_wallet_returns_watch_status_wallet_shape(client_and_engine):
    client, _ = client_and_engine
    response = client.post("/api/wallets", json={"address": "0xNEW", "niche": "crypto"})
    assert response.status_code == 200
    body = response.json()
    assert body["address"] == "0xnew"
    assert body["status"] == "watch"
    assert body["sampleSize"] == 0
    assert body["tags"] == ["manual"]
    assert body["nichesObserved"] == ["crypto"]


def test_add_wallet_without_niche(client_and_engine):
    client, _ = client_and_engine
    response = client.post("/api/wallets", json={"address": "0xNEW"})
    assert response.status_code == 200
    body = response.json()
    assert body["niche"] is None
    assert body["nichesObserved"] == []


def test_added_wallet_appears_in_list(client_and_engine):
    client, _ = client_and_engine
    client.post("/api/wallets", json={"address": "0xNEW", "niche": "crypto"})

    response = client.get("/api/wallets")
    wallets = response.json()
    assert len(wallets) == 1
    assert wallets[0]["address"] == "0xnew"


def test_remove_wallet_success(client_and_engine):
    client, _ = client_and_engine
    client.post("/api/wallets", json={"address": "0xNEW"})

    response = client.delete("/api/wallets/0xNEW")
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    listed = client.get("/api/wallets").json()
    assert listed == []


def test_remove_wallet_not_found_returns_404(client_and_engine):
    client, _ = client_and_engine
    response = client.delete("/api/wallets/0xdoesnotexist")
    assert response.status_code == 404


def test_wallet_with_resolved_trades_maps_classification_to_status(client_and_engine):
    client, engine = client_and_engine
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO markets (market_id, condition_id, question, category, active, closed, end_date) "
                "VALUES ('m1','c1','Q1','sports',0,1,:end_date)"
            ),
            {"end_date": (now - timedelta(days=1)).isoformat()},
        )
        for i in range(60):
            closed_ts = (now - timedelta(days=60 - i)).isoformat()
            conn.execute(
                text(
                    "INSERT INTO wallet_closed_positions "
                    "(wallet, market_id, condition_id, token_id, outcome, size, avg_price, realized_pnl, closed_ts) "
                    "VALUES ('0xabc', 'm1', 'c1', 'tok1', 'YES', 100, 0.4, 20.0, :closed_ts)"
                ),
                {"closed_ts": closed_ts},
            )
            conn.execute(
                text(
                    "INSERT INTO wallet_trades "
                    "(wallet, ts, market_id, condition_id, token_id, outcome, side, price, size, usdc_size) "
                    "VALUES ('0xabc', :ts, 'm1', 'c1', 'tok1', 'YES', 'BUY', 0.4, 100, 40)"
                ),
                {"ts": closed_ts},
            )

    add_wallet("0xabc", label="fixture", source="manual", engine=engine)
    score_all_wallets(engine=engine)

    response = client.get("/api/wallets")
    wallets = response.json()
    assert len(wallets) == 1
    w = wallets[0]
    assert w["address"] == "0xabc"
    assert w["status"] in {"qualified", "watch", "rejected"}
    assert w["resolvedObservations"] == 60
    assert w["source"] == "manual"


def test_wallet_never_reports_unrealized_pnl_as_realized(client_and_engine):
    """Sanity check that the API bridge doesn't undo the realized/unrealized
    separation built into the scoring layer."""
    client, engine = client_and_engine
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO markets (market_id, condition_id, question, category, active, closed, end_date) "
                "VALUES ('m1','c1','Q1','sports',0,1,:end_date)"
            ),
            {"end_date": (now - timedelta(days=1)).isoformat()},
        )
        conn.execute(
            text(
                "INSERT INTO wallet_closed_positions "
                "(wallet, market_id, condition_id, token_id, outcome, size, avg_price, realized_pnl, closed_ts) "
                "VALUES ('0xabc', 'm1', 'c1', 'tok1', 'YES', 100, 0.4, 5.0, :closed_ts)"
            ),
            {"closed_ts": (now - timedelta(days=1)).isoformat()},
        )
        conn.execute(
            text(
                "INSERT INTO wallet_trades "
                "(wallet, ts, market_id, condition_id, token_id, outcome, side, price, size, usdc_size) "
                "VALUES ('0xabc', :ts, 'm1', 'c1', 'tok1', 'YES', 'BUY', 0.4, 100, 40)"
            ),
            {"ts": (now - timedelta(days=1)).isoformat()},
        )
        conn.execute(
            text(
                "INSERT INTO wallet_positions "
                "(wallet, market_id, condition_id, token_id, outcome, size, avg_price, cur_price, cash_pnl, percent_pnl) "
                "VALUES ('0xabc', 'm2', 'c2', 'tok2', 'YES', 50, 0.3, 0.9, 5000, 2.0)"
            )
        )

    add_wallet("0xabc", label="fixture", source="manual", engine=engine)
    score_all_wallets(engine=engine)

    wallets = client.get("/api/wallets").json()
    assert wallets[0]["realizedPnl"] == pytest.approx(5.0)
    assert wallets[0]["realizedPnl"] != pytest.approx(5000.0)
