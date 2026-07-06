from __future__ import annotations

"""
Full wallet activity ingestion (TRADE, SPLIT, MERGE, REDEEM, and anything
else the Data API's /activity endpoint returns).

Why this is separate from ingest/wallets.py
---------------------------------------------
ingest/wallets.py only pulls /trades (BUY/SELL fills). It has no visibility
into SPLIT, MERGE, or REDEEM events, which means a wallet that exits via
MERGE or REDEEM looks (to that module) like it's still holding the
position. This module ingests the full activity feed and normalizes it into
`wallet_lifecycle_events` (see scoring/lifecycle.py for the classification
logic) so we can tell the difference between "still in the trade" and
"exited via a non-trade event".

This module intentionally does NOT feed wallet scoring or signal generation
yet. It exists to get an accurate lifecycle picture first - see the hard
rules in the project's build notes: MERGE/REDEEM/SPLIT are lifecycle
information only until a later task explicitly wires them into signals.

KNOWN API UNCERTAINTY - READ BEFORE TRUSTING THIS
----------------------------------------------------
This build environment has no network egress to polymarket.com, so none of
the parsing below has been run against a real /activity response. Field
names are guessed defensively (multiple candidate keys, same pattern as
ingest/wallets.py and ingest/closed_positions.py) and a row is marked
`parsed_ok=False` with a `parse_warning` when we can't find fields we'd
expect - but the raw row is ALWAYS stored regardless, so nothing is ever
silently dropped even when parsing is uncertain.

Before trusting this for anything real:
  1. Run `ingest_wallet_activity()` against a wallet with known SPLIT/MERGE/
     REDEEM history.
  2. Diff `raw_json` against the parsed columns in `wallet_activity_raw`.
  3. Update the candidate key lists in `_first(...)` if field names differ.
"""

import json
import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from polyalgo.clients.polymarket import PolymarketClient
from polyalgo.db import get_engine
from polyalgo.ingest.tracked_wallets import list_wallets, mark_ingested
from polyalgo.scoring.lifecycle import build_lifecycle_event

logger = logging.getLogger(__name__)


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first(d: dict, *keys):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _extract_activity_records(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "activity", "activities", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def parse_activity_record(wallet: str, r: dict) -> dict:
    """Map one raw /activity record onto our storage schema.

    Never raises. If required fields are missing, `parsed_ok` is set False
    and `parse_warning` explains what's missing - the row is still returned
    for storage with raw_json intact.
    """
    activity_type = _first(r, "type", "activityType", "eventType")
    timestamp = _first(r, "timestamp", "createdAt", "time")
    condition_id = _first(r, "conditionId", "condition_id")
    token_id = _first(r, "asset", "assetId", "tokenId")
    side = _first(r, "side")
    size = _to_float(_first(r, "size", "quantity", "shares"))
    price = _to_float(_first(r, "price"))
    usdc_size = _to_float(_first(r, "usdcSize", "amount", "usdcAmount"))
    tx_hash = _first(r, "transactionHash", "txHash")

    missing = []
    if not activity_type:
        missing.append("activity_type")
    if not timestamp:
        missing.append("timestamp")
    if not condition_id and not token_id:
        missing.append("condition_id_or_token_id")

    parsed_ok = len(missing) == 0
    parse_warning = f"missing fields: {missing}" if missing else None

    if not parsed_ok:
        logger.warning(
            "activity record for %s parsed with missing fields %s (raw keys: %s)",
            wallet,
            missing,
            sorted(r.keys()),
        )

    return {
        "wallet_address": wallet.lower(),
        "activity_type": str(activity_type) if activity_type else None,
        "condition_id": condition_id,
        "token_id": str(token_id) if token_id else None,
        "side": side,
        "size": size,
        "price": price,
        "usdc_size": usdc_size,
        "transaction_hash": tx_hash,
        "timestamp": str(timestamp) if timestamp else None,
        "raw_json": json.dumps(r),
        "parsed_ok": parsed_ok,
        "parse_warning": parse_warning,
    }


def _dedupe_key(row: dict) -> tuple:
    return (
        row["wallet_address"],
        row.get("transaction_hash"),
        row.get("activity_type"),
        row.get("token_id"),
        row.get("timestamp"),
    )


def _existing_dedupe_keys(engine: Engine, wallet: str) -> set[tuple]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT wallet_address, transaction_hash, activity_type, token_id, timestamp
                FROM wallet_activity_raw
                WHERE lower(wallet_address) = lower(:wallet)
            """),
            {"wallet": wallet},
        ).mappings().all()
    return {
        (r["wallet_address"], r["transaction_hash"], r["activity_type"], r["token_id"], r["timestamp"])
        for r in rows
    }


def ingest_wallet_activity(wallet: str, limit: int = 500, engine: Engine | None = None) -> dict:
    """Fetch, parse, dedupe, and store a wallet's full activity feed, then
    build a lifecycle event for every newly-inserted raw row.

    Safe to call repeatedly - already-seen records (by wallet + tx hash +
    activity type + token + timestamp) are skipped rather than duplicated.
    """
    client = PolymarketClient()
    engine = engine or get_engine()

    try:
        payload = client.get_wallet_activity(wallet, limit=limit)
    except Exception as exc:
        logger.error("activity fetch failed for %s: %s", wallet, exc)
        return {"wallet": wallet.lower(), "error": str(exc)}

    raw_records = _extract_activity_records(payload)
    parsed_rows = [parse_activity_record(wallet, r) for r in raw_records if isinstance(r, dict)]

    existing_keys = _existing_dedupe_keys(engine, wallet)

    inserted = 0
    skipped_duplicate = 0
    parse_warnings = 0
    lifecycle_created = 0

    with engine.begin() as conn:
        for row in parsed_rows:
            key = _dedupe_key(row)
            if key in existing_keys:
                skipped_duplicate += 1
                continue
            existing_keys.add(key)

            if row["parse_warning"]:
                parse_warnings += 1

            result = conn.execute(
                text("""
                    INSERT INTO wallet_activity_raw (
                        wallet_address, activity_type, condition_id, token_id, side,
                        size, price, usdc_size, transaction_hash, timestamp,
                        raw_json, parsed_ok, parse_warning
                    ) VALUES (
                        :wallet_address, :activity_type, :condition_id, :token_id, :side,
                        :size, :price, :usdc_size, :transaction_hash, :timestamp,
                        :raw_json, :parsed_ok, :parse_warning
                    )
                """),
                row,
            )
            inserted += 1

            raw_id = result.lastrowid
            raw_row_for_lifecycle = dict(row)
            raw_row_for_lifecycle["id"] = raw_id
            raw_row_for_lifecycle["market_slug"] = None  # not available from /activity alone

            event = build_lifecycle_event(raw_row_for_lifecycle)
            conn.execute(
                text("""
                    INSERT INTO wallet_lifecycle_events (
                        wallet_address, event_type, condition_id, token_id, market_slug,
                        side, size, price, usdc_size, transaction_hash, timestamp,
                        interpretation, raw_activity_id
                    ) VALUES (
                        :wallet_address, :event_type, :condition_id, :token_id, :market_slug,
                        :side, :size, :price, :usdc_size, :transaction_hash, :timestamp,
                        :interpretation, :raw_activity_id
                    )
                """),
                {
                    "wallet_address": event.wallet_address,
                    "event_type": event.event_type,
                    "condition_id": event.condition_id,
                    "token_id": event.token_id,
                    "market_slug": event.market_slug,
                    "side": event.side,
                    "size": event.size,
                    "price": event.price,
                    "usdc_size": event.usdc_size,
                    "transaction_hash": event.transaction_hash,
                    "timestamp": event.timestamp,
                    "interpretation": event.interpretation,
                    "raw_activity_id": event.raw_activity_id,
                },
            )
            lifecycle_created += 1

    mark_ingested(wallet, engine=engine)

    return {
        "wallet": wallet.lower(),
        "fetched": len(raw_records),
        "inserted_raw": inserted,
        "skipped_duplicate": skipped_duplicate,
        "parse_warnings": parse_warnings,
        "lifecycle_events_created": lifecycle_created,
    }


def ingest_tracked_wallets_activity(engine: Engine | None = None) -> list[dict]:
    """Run ingest_wallet_activity for every active tracked wallet."""
    engine = engine or get_engine()
    wallets = list_wallets(active_only=True, engine=engine)
    results = []
    for w in wallets:
        results.append(ingest_wallet_activity(w["wallet_address"], engine=engine))
    return results
