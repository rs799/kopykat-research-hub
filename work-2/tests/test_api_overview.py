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


def test_overview_on_empty_db_is_all_honest_zeros(client_and_engine):
    client, _ = client_and_engine
    response = client.get("/api/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["activeNiches"] == 0  # niche classification not implemented
    assert body["discoveredWallets"] == 0
    assert body["qualifiedWallets"] == 0
    assert body["consensusAlerts"] == 0  # consensus engine not implemented
    assert body["rejectedAlerts"] == 0
    assert body["paperPnl"] == 0
    assert body["parserWarnings"] == 0
    assert body["mode"] == "PAPER ONLY"
    assert body["backendStatus"] == "local"


def _insert_resolved_wallet(engine, wallet: str, n_resolved: int = 25):
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO markets (market_id, condition_id, question, category, active, closed, end_date) "
                "VALUES ('m1','c1','Q1','sports',0,1,:end_date)"
            ),
            {"end_date": (now - timedelta(days=1)).isoformat()},
        )
        for i in range(n_resolved):
            pnl = 20.0 if i % 5 != 0 else -15.0
            closed_ts = (now - timedelta(days=n_resolved - i)).isoformat()
            conn.execute(
                text(
                    "INSERT INTO wallet_closed_positions "
                    "(wallet, market_id, condition_id, token_id, outcome, size, avg_price, realized_pnl, closed_ts) "
                    "VALUES (:wallet, 'm1', 'c1', 'tok1', 'YES', 100, 0.4, :pnl, :closed_ts)"
                ),
                {"wallet": wallet, "pnl": pnl, "closed_ts": closed_ts},
            )
            # score_all_wallets() discovers which wallets to score via
            # wallet_trades, so a fixture needs a matching trade row too.
            conn.execute(
                text(
                    "INSERT INTO wallet_trades "
                    "(wallet, ts, market_id, condition_id, token_id, outcome, side, price, size, usdc_size) "
                    "VALUES (:wallet, :ts, 'm1', 'c1', 'tok1', 'YES', 'BUY', 0.4, 100, 40)"
                ),
                {"wallet": wallet, "ts": closed_ts},
            )


def test_overview_reflects_real_wallet_scores(client_and_engine):
    client, engine = client_and_engine
    _insert_resolved_wallet(engine, "0xabc")
    add_wallet("0xabc", label="fixture", engine=engine)
    score_all_wallets(engine=engine)

    response = client.get("/api/overview")
    body = response.json()
    assert body["discoveredWallets"] == 1


def test_overview_reflects_parser_warnings(client_and_engine):
    client, engine = client_and_engine
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO wallet_activity_raw (wallet_address, activity_type, parsed_ok, parse_warning) "
                "VALUES ('0xabc', NULL, 0, 'missing fields')"
            )
        )

    response = client.get("/api/overview")
    assert response.json()["parserWarnings"] == 1


def test_overview_reflects_paper_pnl(client_and_engine):
    client, engine = client_and_engine
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO paper_positions "
                "(opened_at, market_id, token_id, side, shares, avg_entry, mark_price, realized_pnl, unrealized_pnl, status) "
                "VALUES (CURRENT_TIMESTAMP, 'm1', 'tok1', 'BUY', 100, 0.4, 0.5, 5.0, 10.0, 'open')"
            )
        )

    response = client.get("/api/overview")
    assert response.json()["paperPnl"] == 15.0
