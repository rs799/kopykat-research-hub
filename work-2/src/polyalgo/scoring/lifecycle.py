from __future__ import annotations

"""
Wallet lifecycle classification.

Why this exists
----------------
A wallet's true exposure can't be read off /trades alone. Besides BUY/SELL
trades, Polymarket wallets can also:

  - SPLIT   : lock USDC to mint a full set of YES+NO tokens (construction,
              not a directional bet).
  - MERGE   : combine matched YES+NO tokens back into USDC. This is a real
              exit - the wallet no longer holds the position - but it never
              shows up as a "SELL" in /trades. A signal engine that only
              watches /trades would keep thinking the wallet is still in
              the trade after a MERGE exit.
  - REDEEM  : claim USDC after a market resolves. Also an exit, but driven
              by market resolution rather than a wallet decision.

This module turns a raw activity record's type string into one of our
normalized event types, and attaches a plain-language interpretation. It
does NOT decide whether an event should generate a trading signal - see the
hard rule in ingest/activity.py and CLAUDE_UPDATE_WALLET_ACTIVITY_NEXT.md:
MERGE/REDEEM/SPLIT are lifecycle information only, not signals, until a
later task explicitly wires them in.

UNVERIFIED AGAINST THE LIVE API: the raw `activity_type` strings we classify
here ("TRADE", "SPLIT", "MERGE", "REDEEM") are our best guess at what the
Data API's /activity endpoint actually returns capitalized as. Unknown or
differently-capitalized values fall through to UNKNOWN rather than being
silently misclassified - see `classify_activity_type`.
"""

from dataclasses import dataclass

EVENT_TYPES = {"TRADE_BUY", "TRADE_SELL", "SPLIT", "MERGE", "REDEEM", "UNKNOWN"}

_INTERPRETATIONS = {
    "TRADE_BUY": "possible entry",
    "TRADE_SELL": "possible exit or reduction",
    "MERGE": "exit-like / position reduction / hidden exit candidate",
    "REDEEM": "resolution/settlement event",
    "SPLIT": "position construction / token conversion event",
    "UNKNOWN": "unknown activity type - stored for visibility, not used for signal generation",
}

# Event types that should never be used to generate a copy-trading signal
# until lifecycle-aware signal logic is explicitly built and reviewed.
NON_SIGNAL_EVENT_TYPES = {"MERGE", "REDEEM", "SPLIT", "UNKNOWN"}


def classify_activity_type(raw_activity_type: str | None, side: str | None = None) -> str:
    """Map a raw API activity-type string (+ side, for trades) onto one of
    our normalized event types. Never guesses past what the data supports:
    a TRADE with no usable side comes back UNKNOWN rather than assuming BUY.
    """
    if not raw_activity_type:
        return "UNKNOWN"

    t = raw_activity_type.strip().upper()

    if t == "TRADE":
        s = (side or "").strip().upper()
        if s == "BUY":
            return "TRADE_BUY"
        if s == "SELL":
            return "TRADE_SELL"
        return "UNKNOWN"

    if t in {"SPLIT", "MERGE", "REDEEM"}:
        return t

    return "UNKNOWN"


def interpret_event(event_type: str) -> str:
    return _INTERPRETATIONS.get(event_type, _INTERPRETATIONS["UNKNOWN"])


def is_signal_eligible(event_type: str) -> bool:
    """Whether this event type is currently allowed to feed a trading
    signal. Everything except TRADE_BUY/TRADE_SELL is excluded for now -
    see module docstring."""
    return event_type not in NON_SIGNAL_EVENT_TYPES


@dataclass
class LifecycleEvent:
    wallet_address: str
    event_type: str
    condition_id: str | None
    token_id: str | None
    market_slug: str | None
    side: str | None
    size: float | None
    price: float | None
    usdc_size: float | None
    transaction_hash: str | None
    timestamp: str | None
    interpretation: str
    raw_activity_id: int | None


def build_lifecycle_event(raw_row: dict) -> LifecycleEvent:
    """Build a normalized lifecycle event from a wallet_activity_raw row
    (as a dict - works with both a DB row mapping and a plain dict, e.g. in
    tests). Always returns an event, even for UNKNOWN types - see module
    docstring for why UNKNOWN is stored rather than dropped.
    """
    event_type = classify_activity_type(raw_row.get("activity_type"), raw_row.get("side"))
    return LifecycleEvent(
        wallet_address=(raw_row.get("wallet_address") or "").lower(),
        event_type=event_type,
        condition_id=raw_row.get("condition_id"),
        token_id=raw_row.get("token_id"),
        market_slug=raw_row.get("market_slug"),
        side=raw_row.get("side"),
        size=raw_row.get("size"),
        price=raw_row.get("price"),
        usdc_size=raw_row.get("usdc_size"),
        transaction_hash=raw_row.get("transaction_hash"),
        timestamp=raw_row.get("timestamp"),
        interpretation=interpret_event(event_type),
        raw_activity_id=raw_row.get("id"),
    )
