from polyalgo.scoring.lifecycle import (
    classify_activity_type,
    interpret_event,
    is_signal_eligible,
    build_lifecycle_event,
    NON_SIGNAL_EVENT_TYPES,
)


# ---------------------------------------------------------------------------
# classify_activity_type
# ---------------------------------------------------------------------------


def test_classify_trade_buy():
    assert classify_activity_type("TRADE", "BUY") == "TRADE_BUY"


def test_classify_trade_sell():
    assert classify_activity_type("TRADE", "SELL") == "TRADE_SELL"


def test_classify_trade_is_case_insensitive():
    assert classify_activity_type("trade", "buy") == "TRADE_BUY"


def test_classify_trade_without_side_is_unknown():
    # Never guess a side - a TRADE with no usable side is UNKNOWN, not
    # silently assumed to be a BUY.
    assert classify_activity_type("TRADE", None) == "UNKNOWN"
    assert classify_activity_type("TRADE", "") == "UNKNOWN"
    assert classify_activity_type("TRADE", "SOMETHING_ELSE") == "UNKNOWN"


def test_classify_merge_redeem_split():
    assert classify_activity_type("MERGE") == "MERGE"
    assert classify_activity_type("REDEEM") == "REDEEM"
    assert classify_activity_type("SPLIT") == "SPLIT"


def test_classify_merge_redeem_split_case_insensitive():
    assert classify_activity_type("merge") == "MERGE"
    assert classify_activity_type("Redeem") == "REDEEM"


def test_classify_unknown_type():
    assert classify_activity_type("SOME_FUTURE_TYPE") == "UNKNOWN"


def test_classify_none_or_empty():
    assert classify_activity_type(None) == "UNKNOWN"
    assert classify_activity_type("") == "UNKNOWN"


# ---------------------------------------------------------------------------
# interpret_event
# ---------------------------------------------------------------------------


def test_interpret_known_events():
    assert interpret_event("TRADE_BUY") == "possible entry"
    assert interpret_event("TRADE_SELL") == "possible exit or reduction"
    assert "hidden exit" in interpret_event("MERGE")
    assert "resolution" in interpret_event("REDEEM")
    assert "construction" in interpret_event("SPLIT")


def test_interpret_unknown_event_falls_back_gracefully():
    assert "not used for signal" in interpret_event("UNKNOWN")
    assert "not used for signal" in interpret_event("something_not_in_the_map")


# ---------------------------------------------------------------------------
# is_signal_eligible
# ---------------------------------------------------------------------------


def test_trade_events_are_signal_eligible():
    assert is_signal_eligible("TRADE_BUY") is True
    assert is_signal_eligible("TRADE_SELL") is True


def test_lifecycle_only_events_are_not_signal_eligible():
    assert is_signal_eligible("MERGE") is False
    assert is_signal_eligible("REDEEM") is False
    assert is_signal_eligible("SPLIT") is False
    assert is_signal_eligible("UNKNOWN") is False


def test_non_signal_event_types_constant_matches_behavior():
    for event_type in NON_SIGNAL_EVENT_TYPES:
        assert is_signal_eligible(event_type) is False


# ---------------------------------------------------------------------------
# build_lifecycle_event
# ---------------------------------------------------------------------------


def test_build_lifecycle_event_from_trade_row():
    raw_row = {
        "id": 1,
        "wallet_address": "0xABC",
        "activity_type": "TRADE",
        "side": "BUY",
        "condition_id": "c1",
        "token_id": "tok1",
        "size": 100.0,
        "price": 0.4,
        "usdc_size": 40.0,
        "transaction_hash": "0xh1",
        "timestamp": "2026-01-01T00:00:00Z",
    }
    event = build_lifecycle_event(raw_row)
    assert event.wallet_address == "0xabc"
    assert event.event_type == "TRADE_BUY"
    assert event.interpretation == "possible entry"
    assert event.raw_activity_id == 1


def test_build_lifecycle_event_for_merge_is_stored_not_dropped():
    raw_row = {
        "id": 2,
        "wallet_address": "0xabc",
        "activity_type": "MERGE",
        "side": None,
        "condition_id": "c1",
        "token_id": "tok1",
        "size": 100.0,
        "price": None,
        "usdc_size": None,
        "transaction_hash": "0xh2",
        "timestamp": "2026-01-02T00:00:00Z",
    }
    event = build_lifecycle_event(raw_row)
    assert event.event_type == "MERGE"
    assert "hidden exit" in event.interpretation


def test_build_lifecycle_event_for_unknown_type_is_still_stored():
    raw_row = {
        "id": 3,
        "wallet_address": "0xabc",
        "activity_type": "SOME_NEW_TYPE",
        "side": None,
        "condition_id": None,
        "token_id": "tok1",
        "size": None,
        "price": None,
        "usdc_size": None,
        "transaction_hash": "0xh3",
        "timestamp": "2026-01-03T00:00:00Z",
    }
    event = build_lifecycle_event(raw_row)
    assert event.event_type == "UNKNOWN"
    assert event.raw_activity_id == 3
    assert is_signal_eligible(event.event_type) is False
