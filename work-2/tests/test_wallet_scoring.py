from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from polyalgo.db import init_db
from polyalgo.scoring.wallets import (
    bayesian_shrink,
    sample_reliability,
    clamp,
    score_from_edge,
    classify_wallet,
    compute_drawdown_score,
    compute_niche_score,
    compute_recency_score,
    compute_liquidity_adjusted_score,
    compute_exit_quality_score,
    compute_penalties,
    compute_wallet_score,
    score_all_wallets,
)


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------


def test_bayesian_shrink_zero_sample_returns_baseline():
    assert bayesian_shrink(observed=1.0, n=0, baseline=0.1, k=100) == 0.1


def test_bayesian_shrink_large_sample_moves_toward_observed():
    value = bayesian_shrink(observed=0.2, n=1000, baseline=0.0, k=100)
    assert 0.18 < value < 0.2


def test_bayesian_shrink_rejects_negative_n():
    with pytest.raises(ValueError):
        bayesian_shrink(0.1, n=-1)


def test_sample_reliability_bounds():
    assert sample_reliability(0) == 0.0
    assert 0.0 < sample_reliability(50) < 1.0
    assert sample_reliability(100000) == 1.0


def test_clamp():
    assert clamp(1.5) == 1.0
    assert clamp(-0.5) == 0.0
    assert clamp(0.3) == 0.3


def test_score_from_edge_none_returns_center():
    assert score_from_edge(None, k=5.0) == 0.5
    assert score_from_edge(None, k=5.0, center=0.7) == 0.7


def test_score_from_edge_positive_and_negative():
    assert score_from_edge(0.1, k=5.0) == pytest.approx(1.0)
    assert score_from_edge(-0.5, k=5.0) == 0.0
    assert score_from_edge(0.0, k=5.0) == 0.5


def test_classify_wallet_insufficient_sample():
    assert classify_wallet(95, resolved_trade_count=5) == "insufficient_sample"


def test_classify_wallet_tiers():
    assert classify_wallet(85, resolved_trade_count=25) == "candidate_smart_wallet"
    assert classify_wallet(70, resolved_trade_count=25) == "watchlist"
    assert classify_wallet(40, resolved_trade_count=25) == "ignore"


# ---------------------------------------------------------------------------
# Drawdown
# ---------------------------------------------------------------------------


def test_drawdown_neutral_when_too_few_dated_trades():
    positions = [{"closed_ts": "2026-01-01T00:00:00Z", "realized_pnl": 10.0}]
    comp = compute_drawdown_score(positions)
    assert comp.raw_score == 0.5


def test_drawdown_scores_lower_for_bigger_relative_drawdown():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def mk(days, pnl):
        return {"closed_ts": (base + timedelta(days=days)).isoformat(), "realized_pnl": pnl}

    smooth = [mk(i, 10.0) for i in range(6)]
    smooth_comp = compute_drawdown_score(smooth)

    volatile = [mk(0, 60.0)] + [mk(i, -9.0) for i in range(1, 6)]
    volatile_comp = compute_drawdown_score(volatile)

    assert smooth_comp.raw_score > volatile_comp.raw_score


def test_drawdown_neutral_when_cumulative_never_positive():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    positions = [
        {"closed_ts": (base + timedelta(days=i)).isoformat(), "realized_pnl": -5.0} for i in range(6)
    ]
    comp = compute_drawdown_score(positions)
    assert comp.raw_score == 0.5


# ---------------------------------------------------------------------------
# Niche specialization
# ---------------------------------------------------------------------------


def test_niche_neutral_when_no_category_has_enough_trades():
    positions = [
        {"category": "sports", "size": 10, "avg_price": 0.5, "realized_pnl": 5.0} for _ in range(2)
    ]
    comp = compute_niche_score(positions)
    assert comp.raw_score == 0.5


def test_niche_picks_best_category():
    good = [
        {"category": "sports", "size": 100, "avg_price": 0.5, "realized_pnl": 50.0} for _ in range(6)
    ]
    bad = [
        {"category": "politics", "size": 100, "avg_price": 0.5, "realized_pnl": -50.0} for _ in range(6)
    ]
    comp = compute_niche_score(good + bad)
    assert comp.raw_score > 0.5
    assert "sports" in comp.note


# ---------------------------------------------------------------------------
# Recency
# ---------------------------------------------------------------------------


def test_recency_neutral_with_too_few_trades():
    positions = [
        {
            "closed_ts": datetime.now(timezone.utc).isoformat(),
            "realized_pnl": 5.0,
            "size": 10,
            "avg_price": 0.5,
        }
    ]
    comp = compute_recency_score(positions)
    assert comp.raw_score == 0.5


def test_recency_weights_recent_trades_more():
    now = datetime.now(timezone.utc)

    def mk(days_ago, pnl):
        return {
            "closed_ts": (now - timedelta(days=days_ago)).isoformat(),
            "realized_pnl": pnl,
            "size": 100,
            "avg_price": 0.5,
        }

    positions = [mk(200, -20.0) for _ in range(3)] + [mk(1, 20.0) for _ in range(3)]
    comp = compute_recency_score(positions, as_of=now)
    assert comp.raw_score > 0.5


# ---------------------------------------------------------------------------
# Liquidity-adjusted PnL
# ---------------------------------------------------------------------------


def test_liquidity_neutral_when_no_depth_data():
    positions = [{"token_id": "tok1", "realized_pnl": 10.0}]
    comp = compute_liquidity_adjusted_score(positions, depth_by_token={})
    assert comp.raw_score == 0.5
    assert "no orderbook depth" in comp.note


def test_liquidity_penalizes_thin_book_concentration():
    positions = [
        {"token_id": "thin", "realized_pnl": 90.0},
        {"token_id": "deep", "realized_pnl": 10.0},
    ]
    depth = {"thin": 50.0, "deep": 5000.0}
    comp = compute_liquidity_adjusted_score(positions, depth_by_token=depth)
    assert comp.raw_score < 0.5


def test_liquidity_neutral_when_net_pnl_not_positive():
    positions = [{"token_id": "thin", "realized_pnl": -10.0}]
    comp = compute_liquidity_adjusted_score(positions, depth_by_token={"thin": 50.0})
    assert comp.raw_score == 0.5


# ---------------------------------------------------------------------------
# Exit quality (documented as not implemented)
# ---------------------------------------------------------------------------


def test_exit_quality_is_honestly_neutral():
    comp = compute_exit_quality_score()
    assert comp.raw_score == 0.5
    assert "not implemented" in comp.note.lower()


# ---------------------------------------------------------------------------
# Penalties
# ---------------------------------------------------------------------------


def test_penalty_low_sample_size():
    penalties = compute_penalties(resolved_trade_count=10, closed_positions=[], avg_clv_24h=None)
    names = [p.name for p in penalties]
    assert "low_sample_size" in names
    pts = next(p.points for p in penalties if p.name == "low_sample_size")
    assert pts == 15.0


def test_penalty_moderate_sample_size():
    penalties = compute_penalties(resolved_trade_count=30, closed_positions=[], avg_clv_24h=None)
    pts = next(p.points for p in penalties if p.name == "low_sample_size")
    assert pts == 5.0


def test_penalty_none_for_large_sample():
    penalties = compute_penalties(resolved_trade_count=100, closed_positions=[], avg_clv_24h=None)
    assert all(p.name != "low_sample_size" for p in penalties)


def test_penalty_one_hit_wonder():
    positions = [{"realized_pnl": 1000.0, "market_id": "m1"}] + [
        {"realized_pnl": 1.0, "market_id": f"m{i}"} for i in range(2, 22)
    ]
    penalties = compute_penalties(resolved_trade_count=21, closed_positions=positions, avg_clv_24h=0.02)
    assert any(p.name == "one_hit_wonder" for p in penalties)


def test_penalty_negative_clv():
    penalties = compute_penalties(resolved_trade_count=50, closed_positions=[], avg_clv_24h=-0.05)
    assert any(p.name == "negative_clv" for p in penalties)


def test_penalty_no_negative_clv_when_positive():
    penalties = compute_penalties(resolved_trade_count=50, closed_positions=[], avg_clv_24h=0.05)
    assert all(p.name != "negative_clv" for p in penalties)


def test_penalty_concentration_risk():
    positions = [{"realized_pnl": 100.0, "market_id": "m1"}] * 10 + [
        {"realized_pnl": 5.0, "market_id": f"m{i}"} for i in range(2, 12)
    ]
    penalties = compute_penalties(resolved_trade_count=20, closed_positions=positions, avg_clv_24h=0.01)
    assert any(p.name == "concentration_risk" for p in penalties)


# ---------------------------------------------------------------------------
# End-to-end integration using an isolated in-memory SQLite DB
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}, future=True
    )
    init_db(engine)
    yield engine


def _insert_wallet_fixture(engine, wallet: str, n_resolved: int, win_pnl: float, loss_pnl: float):
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
            pnl = win_pnl if i % 5 != 0 else loss_pnl
            conn.execute(
                text(
                    "INSERT INTO wallet_closed_positions "
                    "(wallet, market_id, condition_id, token_id, outcome, size, avg_price, realized_pnl, closed_ts) "
                    "VALUES (:wallet, 'm1', 'c1', 'tok1', 'YES', 100, 0.4, :pnl, :closed_ts)"
                ),
                {"wallet": wallet, "pnl": pnl, "closed_ts": (now - timedelta(days=n_resolved - i)).isoformat()},
            )
            conn.execute(
                text(
                    "INSERT INTO wallet_trades "
                    "(wallet, ts, market_id, condition_id, token_id, outcome, side, price, size, usdc_size) "
                    "VALUES (:wallet, :ts, 'm1', 'c1', 'tok1', 'YES', 'BUY', 0.4, 100, 40)"
                ),
                {"wallet": wallet, "ts": (now - timedelta(days=n_resolved - i)).isoformat()},
            )
        conn.execute(
            text(
                "INSERT INTO wallet_positions "
                "(wallet, market_id, condition_id, token_id, outcome, size, avg_price, cur_price, cash_pnl, percent_pnl) "
                "VALUES (:wallet, 'm2', 'c2', 'tok2', 'YES', 50, 0.3, 0.9, 3000, 2.0)"
            ),
            {"wallet": wallet},
        )


def test_compute_wallet_score_excludes_unrealized_pnl(db_engine):
    wallet = "0xabc"
    _insert_wallet_fixture(db_engine, wallet, n_resolved=25, win_pnl=20.0, loss_pnl=-15.0)

    score = compute_wallet_score(wallet, engine=db_engine)

    assert score.unrealized_pnl == pytest.approx(3000.0)
    assert score.realized_pnl != pytest.approx(3000.0)
    assert score.resolved_trade_count == 25
    assert score.classification in {"watchlist", "candidate_smart_wallet", "ignore"}


def test_compute_wallet_score_insufficient_sample(db_engine):
    wallet = "0xdef"
    _insert_wallet_fixture(db_engine, wallet, n_resolved=3, win_pnl=20.0, loss_pnl=-15.0)

    score = compute_wallet_score(wallet, engine=db_engine)
    assert score.classification == "insufficient_sample"


def test_compute_wallet_score_component_json_is_valid(db_engine):
    import json

    wallet = "0xghi"
    _insert_wallet_fixture(db_engine, wallet, n_resolved=25, win_pnl=20.0, loss_pnl=-15.0)

    score = compute_wallet_score(wallet, engine=db_engine)
    breakdown = json.loads(score.component_json)
    assert "components" in breakdown
    assert len(breakdown["components"]) == 9
    total_weight = sum(c["weight"] for c in breakdown["components"])
    assert total_weight == 100


def test_score_all_wallets_persists_to_db(db_engine):
    wallet = "0xjkl"
    _insert_wallet_fixture(db_engine, wallet, n_resolved=25, win_pnl=20.0, loss_pnl=-15.0)

    scores = score_all_wallets(engine=db_engine)
    assert len(scores) == 1

    with db_engine.begin() as conn:
        row = conn.execute(
            text("SELECT wallet, final_score, resolved_trade_count FROM wallet_scores WHERE wallet = :w"),
            {"w": wallet},
        ).mappings().first()

    assert row is not None
    assert row["resolved_trade_count"] == 25
