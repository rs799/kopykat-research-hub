from datetime import datetime, timedelta, timezone

import pytest

from polyalgo.scoring.clv import (
    compute_trade_clv,
    is_clv_eligible_side,
    _extract_history_points,
    _nearest_price,
    _parse_ts,
)


def test_is_clv_eligible_side():
    assert is_clv_eligible_side("BUY") is True
    assert is_clv_eligible_side("buy") is True
    assert is_clv_eligible_side("SELL") is False
    assert is_clv_eligible_side(None) is False
    assert is_clv_eligible_side("") is False


def test_parse_ts_handles_iso_and_epoch():
    dt = _parse_ts("2026-01-01T00:00:00Z")
    assert dt.year == 2026 and dt.month == 1 and dt.day == 1

    epoch_seconds = 1735689600  # 2025-01-01T00:00:00Z
    dt2 = _parse_ts(epoch_seconds)
    assert dt2.year == 2025

    epoch_ms = 1735689600000
    dt3 = _parse_ts(epoch_ms)
    assert dt3.year == 2025

    assert _parse_ts(None) is None
    assert _parse_ts("not-a-date") is None


def test_extract_history_points_from_dict_payload():
    payload = {"history": [{"t": 1000, "p": 0.4}, {"t": 2000, "p": 0.45}]}
    points = _extract_history_points(payload)
    assert len(points) == 2
    assert points[0][1] == 0.4
    assert points[1][1] == 0.45
    # sorted ascending by time
    assert points[0][0] < points[1][0]


def test_extract_history_points_from_list_payload():
    payload = [{"timestamp": 1000, "price": 0.5}]
    points = _extract_history_points(payload)
    assert len(points) == 1
    assert points[0][1] == 0.5


def test_extract_history_points_ignores_malformed_entries():
    payload = {"history": [{"t": 1000}, {"p": 0.5}, "not-a-dict", {"t": 2000, "p": "bad"}]}
    points = _extract_history_points(payload)
    assert points == []


def test_nearest_price_within_tolerance():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [(base, 0.4), (base + timedelta(minutes=30), 0.5)]
    target = base + timedelta(minutes=25)
    price = _nearest_price(points, target, tolerance_seconds=45 * 60)
    assert price == 0.5


def test_nearest_price_returns_none_outside_tolerance():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [(base, 0.4)]
    target = base + timedelta(hours=5)
    assert _nearest_price(points, target, tolerance_seconds=45 * 60) is None


def test_nearest_price_returns_none_for_empty_points():
    assert _nearest_price([], datetime.now(timezone.utc)) is None


def _make_fetcher(points_by_hour_offset: dict[int, float]):
    """Builds a fake fetch_history function returning synthetic price points
    at given hour offsets from whatever start_ts is requested."""

    def fetch(token_id, start_ts, end_ts):
        history = []
        for offset_hours, price in points_by_hour_offset.items():
            t = start_ts + offset_hours * 3600
            history.append({"t": t, "p": price})
        return {"history": history}

    return fetch


def test_compute_trade_clv_buy_side_positive_move():
    entry_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    close_ts = entry_ts + timedelta(hours=48)
    fetch = _make_fetcher({0: 0.40, 1: 0.42, 6: 0.50, 24: 0.60, 48: 0.70})

    result = compute_trade_clv(
        token_id="tok1",
        side="BUY",
        entry_price=0.40,
        entry_ts=entry_ts,
        close_ts=close_ts,
        fetch_history=fetch,
    )

    assert result is not None
    assert result.clv["1h"] == pytest.approx(0.02, abs=1e-6)
    assert result.clv["6h"] == pytest.approx(0.10, abs=1e-6)
    assert result.clv["24h"] == pytest.approx(0.20, abs=1e-6)
    assert result.clv["close"] == pytest.approx(0.30, abs=1e-6)
    assert all(v is False for v in result.missing.values())


def test_compute_trade_clv_sell_side_is_skipped():
    entry_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fetch = _make_fetcher({1: 0.5})
    result = compute_trade_clv(
        token_id="tok1",
        side="SELL",
        entry_price=0.40,
        entry_ts=entry_ts,
        close_ts=None,
        fetch_history=fetch,
    )
    assert result is None


def test_compute_trade_clv_missing_data_is_flagged_not_guessed():
    entry_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Only a 1h point exists; 6h/24h/close should come back missing.
    fetch = _make_fetcher({1: 0.42})

    result = compute_trade_clv(
        token_id="tok1",
        side="BUY",
        entry_price=0.40,
        entry_ts=entry_ts,
        close_ts=entry_ts + timedelta(hours=72),
        fetch_history=fetch,
    )

    assert result is not None
    assert result.missing["1h"] is False
    assert result.missing["6h"] is True
    assert result.missing["24h"] is True
    assert result.missing["close"] is True
    assert result.clv["6h"] is None
    assert result.clv["24h"] is None
    assert result.clv["close"] is None
    # never substitute a nearby price for a missing horizon
    assert result.prices["6h"] is None


def test_compute_trade_clv_no_close_ts_marks_close_missing():
    entry_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fetch = _make_fetcher({1: 0.42, 6: 0.5, 24: 0.6})

    result = compute_trade_clv(
        token_id="tok1",
        side="BUY",
        entry_price=0.40,
        entry_ts=entry_ts,
        close_ts=None,
        fetch_history=fetch,
    )

    assert result is not None
    assert result.missing["close"] is True
    assert result.clv["close"] is None
    # other horizons still computed fine
    assert result.missing["24h"] is False


def test_compute_trade_clv_fetch_failure_marks_everything_missing_not_raises():
    entry_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def broken_fetch(token_id, start_ts, end_ts):
        raise RuntimeError("network down")

    result = compute_trade_clv(
        token_id="tok1",
        side="BUY",
        entry_price=0.40,
        entry_ts=entry_ts,
        close_ts=entry_ts + timedelta(hours=24),
        fetch_history=broken_fetch,
    )

    assert result is not None
    assert all(result.missing.values())
    assert all(v is None for v in result.clv.values())
