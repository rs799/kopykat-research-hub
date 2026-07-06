-- Migration 002: resolved-position PnL and closing-line value (CLV) storage.
--
-- These tables exist to keep "proven" performance (resolved markets, realized
-- PnL) strictly separate from "unproven" performance (open positions,
-- unrealized/mark-to-market PnL in wallet_positions from 001_init.sql).
--
-- NOTE ON PORTABILITY: like 001_init.sql, this uses SQLite's
-- INTEGER PRIMARY KEY AUTOINCREMENT. If/when this project moves to Postgres,
-- these will need to become SERIAL/IDENTITY columns. Flagged as a known
-- limitation rather than fixed here to keep this migration focused.

CREATE TABLE IF NOT EXISTS wallet_closed_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet TEXT,
    market_id TEXT,
    condition_id TEXT,
    token_id TEXT,
    outcome TEXT,
    size REAL,
    avg_price REAL,
    realized_pnl REAL,
    realized_pnl_pct REAL,
    resolved_price REAL,
    closed_ts TEXT,
    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP,
    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_wallet_closed_positions_wallet ON wallet_closed_positions(wallet);
CREATE INDEX IF NOT EXISTS idx_wallet_closed_positions_market ON wallet_closed_positions(market_id);

-- Per-trade closing-line value. One row per (wallet, wallet_trade) pair that
-- was eligible for CLV calculation (BUY/entry trades only - see scoring/clv.py).
CREATE TABLE IF NOT EXISTS wallet_trade_clv (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet TEXT,
    wallet_trade_id INTEGER,
    market_id TEXT,
    token_id TEXT,
    side TEXT,
    entry_price REAL,
    entry_ts TEXT,
    price_1h REAL,
    price_6h REAL,
    price_24h REAL,
    price_close REAL,
    clv_1h REAL,
    clv_6h REAL,
    clv_24h REAL,
    clv_close REAL,
    missing_1h BOOLEAN,
    missing_6h BOOLEAN,
    missing_24h BOOLEAN,
    missing_close BOOLEAN,
    computed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_wallet_trade_clv_wallet ON wallet_trade_clv(wallet);
CREATE INDEX IF NOT EXISTS idx_wallet_trade_clv_trade ON wallet_trade_clv(wallet_trade_id);
