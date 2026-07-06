import json
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from polyalgo.db import init_db
from polyalgo.ingest.activity import (
    parse_activity_record,
    _extract_activity_records,
    _dedupe_key,
    ingest_wallet_activity,
)
from polyalgo.ingest.tracked_wallets import add_wallet


# ---------------------------------------------------------------------------
# parse_activity_record
# ---------------------------------------------------------------------------


def test_parse_trade_buy():
    row = parse_activity_record(
        "0xABC",
        {
            "type": "TRADE",
            "side": "BUY",
            "conditionId": "c1",
            "asset": "tok1",
            "size": 100,
            "price": 0.4,
            "timestamp": "2026-01-01T00:00:00Z",
            "transactionHash": "0xh1",
        },
    )
    assert row["wallet_address"] == "0xabc"
    assert row["activity_type"] == "TRADE"
    assert row["side"] == "BUY"
    assert row["size"] == 100.0
    assert row["price"] == 0.4
    assert row["parsed_ok"] is True
    assert row["parse_warning"] is None
    # raw_json always preserved verbatim
    assert json.loads(row["raw_json"])["conditionId"] == "c1"


def test_parse_trade_sell():
    row = parse_activity_record(
        "0xabc", {"type": "TRADE", "side": "SELL", "asset": "tok1", "timestamp": "2026-01-01T00:00:00Z"}
    )
    assert row["activity_type"] == "TRADE"
    assert row["side"] == "SELL"
    assert row["parsed_ok"] is True


def test_parse_merge():
    row = parse_activity_record(
        "0xabc",
        {"type": "MERGE", "conditionId": "c1", "asset": "tok1", "size": 50, "timestamp": "2026-01-02T00:00:00Z"},
    )
    assert row["activity_type"] == "MERGE"
    assert row["parsed_ok"] is True


def test_parse_redeem():
    row = parse_activity_record(
        "0xabc",
        {"type": "REDEEM", "conditionId": "c2", "asset": "tok2", "size": 30, "timestamp": "2026-01-03T00:00:00Z"},
    )
    assert row["activity_type"] == "REDEEM"
    assert row["parsed_ok"] is True


def test_parse_split():
    row = parse_activity_record(
        "0xabc",
        {"type": "SPLIT", "conditionId": "c3", "asset": "tok3", "size": 20, "timestamp": "2026-01-04T00:00:00Z"},
    )
    assert row["activity_type"] == "SPLIT"
    assert row["parsed_ok"] is True


def test_parse_unknown_activity_type_does_not_crash():
    row = parse_activity_record(
        "0xabc",
        {"type": "SOME_FUTURE_TYPE", "conditionId": "c4", "timestamp": "2026-01-05T00:00:00Z"},
    )
    # storage schema records the raw type verbatim; classification into our
    # normalized UNKNOWN bucket happens later in scoring/lifecycle.py
    assert row["activity_type"] == "SOME_FUTURE_TYPE"
    assert row["parsed_ok"] is True


def test_parse_missing_fields_flags_not_raises():
    row = parse_activity_record("0xabc", {"foo": "bar"})
    assert row["parsed_ok"] is False
    assert "activity_type" in row["parse_warning"]
    assert "timestamp" in row["parse_warning"]
    # raw_json still preserved even though nothing else parsed
    assert json.loads(row["raw_json"]) == {"foo": "bar"}


def test_parse_missing_condition_and_token_flags_warning():
    row = parse_activity_record(
        "0xabc", {"type": "TRADE", "side": "BUY", "timestamp": "2026-01-01T00:00:00Z"}
    )
    assert row["parsed_ok"] is False
    assert "condition_id_or_token_id" in row["parse_warning"]


def test_parse_never_raises_on_weird_input():
    # Should not raise even with unexpected types in values.
    row = parse_activity_record("0xabc", {"type": "TRADE", "size": "not-a-number", "timestamp": None})
    assert row["size"] is None
    assert row["parsed_ok"] is False


# ---------------------------------------------------------------------------
# _extract_activity_records
# ---------------------------------------------------------------------------


def test_extract_activity_records_from_list():
    assert _extract_activity_records([{"a": 1}]) == [{"a": 1}]


def test_extract_activity_records_from_dict_data_key():
    assert _extract_activity_records({"data": [{"a": 1}]}) == [{"a": 1}]


def test_extract_activity_records_from_dict_activity_key():
    assert _extract_activity_records({"activity": [{"a": 1}]}) == [{"a": 1}]


def test_extract_activity_records_handles_garbage():
    assert _extract_activity_records(None) == []
    assert _extract_activity_records("not a payload") == []
    assert _extract_activity_records({}) == []


# ---------------------------------------------------------------------------
# Dedupe key
# ---------------------------------------------------------------------------


def test_dedupe_key_is_stable():
    row = {
        "wallet_address": "0xabc",
        "transaction_hash": "0xh1",
        "activity_type": "TRADE",
        "token_id": "tok1",
        "timestamp": "2026-01-01T00:00:00Z",
    }
    assert _dedupe_key(row) == _dedupe_key(dict(row))


# ---------------------------------------------------------------------------
# End-to-end ingest with dedupe, using an isolated in-memory DB
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}, future=True
    )
    init_db(engine)
    yield engine


def test_ingest_wallet_activity_stores_all_event_types(db_engine):
    add_wallet("0xabc", label="test", engine=db_engine)

    fake_payload = {
        "data": [
            {
                "type": "TRADE",
                "side": "BUY",
                "conditionId": "c1",
                "asset": "tok1",
                "size": 100,
                "price": 0.4,
                "timestamp": "2026-01-01T00:00:00Z",
                "transactionHash": "0xh1",
            },
            {
                "type": "MERGE",
                "conditionId": "c1",
                "asset": "tok1",
                "size": 100,
                "timestamp": "2026-01-02T00:00:00Z",
                "transactionHash": "0xh2",
            },
            {
                "type": "REDEEM",
                "conditionId": "c2",
                "asset": "tok2",
                "size": 50,
                "timestamp": "2026-01-03T00:00:00Z",
                "transactionHash": "0xh3",
            },
            {
                "type": "SPLIT",
                "conditionId": "c3",
                "asset": "tok3",
                "size": 20,
                "timestamp": "2026-01-04T00:00:00Z",
                "transactionHash": "0xh4",
            },
            {"foo": "bar"},  # malformed - must not crash the batch
        ]
    }

    with patch("polyalgo.ingest.activity.PolymarketClient") as MockClient:
        MockClient.return_value.get_wallet_activity.return_value = fake_payload
        result = ingest_wallet_activity("0xabc", engine=db_engine)

    assert result["fetched"] == 5
    assert result["inserted_raw"] == 5
    assert result["parse_warnings"] == 1
    assert result["lifecycle_events_created"] == 5

    with db_engine.begin() as conn:
        event_types = {
            r["event_type"]
            for r in conn.execute(
                text("SELECT event_type FROM wallet_lifecycle_events WHERE lower(wallet_address) = '0xabc'")
            ).mappings().all()
        }
    assert event_types == {"TRADE_BUY", "MERGE", "REDEEM", "SPLIT", "UNKNOWN"}


def test_ingest_wallet_activity_dedupes_on_rerun(db_engine):
    add_wallet("0xabc", label="test", engine=db_engine)
    fake_payload = {
        "data": [
            {
                "type": "TRADE",
                "side": "BUY",
                "conditionId": "c1",
                "asset": "tok1",
                "size": 100,
                "price": 0.4,
                "timestamp": "2026-01-01T00:00:00Z",
                "transactionHash": "0xh1",
            }
        ]
    }

    with patch("polyalgo.ingest.activity.PolymarketClient") as MockClient:
        MockClient.return_value.get_wallet_activity.return_value = fake_payload
        first = ingest_wallet_activity("0xabc", engine=db_engine)
        second = ingest_wallet_activity("0xabc", engine=db_engine)

    assert first["inserted_raw"] == 1
    assert second["inserted_raw"] == 0
    assert second["skipped_duplicate"] == 1

    with db_engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) AS n FROM wallet_activity_raw")).mappings().first()["n"]
    assert count == 1


def test_ingest_wallet_activity_raw_json_always_preserved(db_engine):
    add_wallet("0xabc", label="test", engine=db_engine)
    fake_payload = {"data": [{"totally": "unexpected", "shape": True}]}

    with patch("polyalgo.ingest.activity.PolymarketClient") as MockClient:
        MockClient.return_value.get_wallet_activity.return_value = fake_payload
        result = ingest_wallet_activity("0xabc", engine=db_engine)

    assert result["inserted_raw"] == 1
    assert result["parse_warnings"] == 1

    with db_engine.begin() as conn:
        row = conn.execute(
            text("SELECT raw_json, parsed_ok FROM wallet_activity_raw WHERE lower(wallet_address) = '0xabc'")
        ).mappings().first()

    assert json.loads(row["raw_json"]) == {"totally": "unexpected", "shape": True}
    assert row["parsed_ok"] in (0, False)


def test_ingest_wallet_activity_handles_client_error_gracefully(db_engine):
    add_wallet("0xabc", label="test", engine=db_engine)
    with patch("polyalgo.ingest.activity.PolymarketClient") as MockClient:
        MockClient.return_value.get_wallet_activity.side_effect = RuntimeError("network down")
        result = ingest_wallet_activity("0xabc", engine=db_engine)

    assert "error" in result
    assert result["wallet"] == "0xabc"
