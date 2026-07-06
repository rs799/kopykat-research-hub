-- Migration 003: tracked wallets + full wallet activity/lifecycle tracking.
--
-- Why this exists: wallet_trades (001_init.sql) only captures the Data API's
-- /trades endpoint, which is BUY/SELL taker fills. It does NOT capture
-- SPLIT, MERGE, or REDEEM events. A wallet can exit a position via MERGE
-- (converting matched YES+NO shares back to USDC) or REDEEM (settlement
-- after resolution) without ever showing up as a "SELL" in /trades. If we
-- only ever look at wallet_trades, we can think a wallet is still holding a
-- position it has actually already exited.
--
-- This migration adds a separate, append-only activity pipeline
-- (wallet_activity_raw -> wallet_lifecycle_events) that is intentionally
-- NOT wired into scoring yet - see scoring/lifecycle.py. It exists to build
-- an accurate picture of wallet lifecycle first - using it for signals is a
-- later, separate task.
--
-- PORTABILITY NOTE: same as 001/002 - uses SQLite's
-- INTEGER PRIMARY KEY AUTOINCREMENT, flagged as a known limitation.

CREATE TABLE IF NOT EXISTS tracked_wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT UNIQUE,
    label TEXT,
    source TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_ingested_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tracked_wallets_active ON tracked_wallets(is_active);

-- Raw activity records exactly as received from the Data API's /activity
-- endpoint (or whatever endpoint turns out to be correct - unverified
-- against the live API from this build environment, see ingest/activity.py
-- docstring). raw_json is ALWAYS stored, even when parsing fails.
CREATE TABLE IF NOT EXISTS wallet_activity_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT,
    activity_type TEXT,
    condition_id TEXT,
    token_id TEXT,
    side TEXT,
    size REAL,
    price REAL,
    usdc_size REAL,
    transaction_hash TEXT,
    timestamp TEXT,
    raw_json TEXT,
    parsed_ok BOOLEAN,
    parse_warning TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_activity_raw_wallet ON wallet_activity_raw(wallet_address);
CREATE INDEX IF NOT EXISTS idx_activity_raw_dedupe
    ON wallet_activity_raw(wallet_address, transaction_hash, activity_type, token_id, timestamp);

-- Normalized lifecycle events derived from wallet_activity_raw. One row per
-- raw activity row (including UNKNOWN types - stored, but excluded from any
-- future signal generation until explicitly enabled).
CREATE TABLE IF NOT EXISTS wallet_lifecycle_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT,
    event_type TEXT,
    condition_id TEXT,
    token_id TEXT,
    market_slug TEXT,
    side TEXT,
    size REAL,
    price REAL,
    usdc_size REAL,
    transaction_hash TEXT,
    timestamp TEXT,
    interpretation TEXT,
    raw_activity_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lifecycle_wallet ON wallet_lifecycle_events(wallet_address);
CREATE INDEX IF NOT EXISTS idx_lifecycle_raw_activity ON wallet_lifecycle_events(raw_activity_id);
