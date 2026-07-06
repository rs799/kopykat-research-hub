CREATE TABLE IF NOT EXISTS markets (
    market_id TEXT PRIMARY KEY,
    condition_id TEXT,
    question TEXT,
    slug TEXT,
    category TEXT,
    tags TEXT,
    outcomes TEXT,
    outcome_prices TEXT,
    clob_token_ids TEXT,
    enable_orderbook BOOLEAN,
    active BOOLEAN,
    closed BOOLEAN,
    end_date TEXT,
    raw_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_markets_condition_id ON markets(condition_id);
CREATE INDEX IF NOT EXISTS idx_markets_active_closed ON markets(active, closed);

CREATE TABLE IF NOT EXISTS orderbook_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT DEFAULT CURRENT_TIMESTAMP,
    market_id TEXT,
    condition_id TEXT,
    token_id TEXT,
    best_bid REAL,
    best_ask REAL,
    midpoint REAL,
    spread REAL,
    depth_1c REAL,
    depth_3c REAL,
    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_books_token_ts ON orderbook_snapshots(token_id, ts);

CREATE TABLE IF NOT EXISTS wallet_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet TEXT,
    ts TEXT,
    market_id TEXT,
    condition_id TEXT,
    token_id TEXT,
    outcome TEXT,
    side TEXT,
    price REAL,
    size REAL,
    usdc_size REAL,
    tx_hash TEXT,
    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_wallet_trades_wallet ON wallet_trades(wallet);
CREATE INDEX IF NOT EXISTS idx_wallet_trades_market ON wallet_trades(market_id);

CREATE TABLE IF NOT EXISTS wallet_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet TEXT,
    ts TEXT DEFAULT CURRENT_TIMESTAMP,
    market_id TEXT,
    condition_id TEXT,
    token_id TEXT,
    outcome TEXT,
    size REAL,
    avg_price REAL,
    cur_price REAL,
    cash_pnl REAL,
    percent_pnl REAL,
    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_wallet_positions_wallet ON wallet_positions(wallet);

CREATE TABLE IF NOT EXISTS wallet_scores (
    wallet TEXT PRIMARY KEY,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    total_trades INTEGER,
    sample_reliability REAL,
    roi_estimate REAL,
    shrunk_roi REAL,
    clv_score REAL,
    drawdown_score REAL,
    timing_score REAL,
    niche_score REAL,
    penalty REAL,
    final_score REAL,
    classification TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT DEFAULT CURRENT_TIMESTAMP,
    market_id TEXT,
    condition_id TEXT,
    token_id TEXT,
    strategy TEXT,
    side TEXT,
    fair_probability REAL,
    entry_price REAL,
    gross_edge REAL,
    estimated_fee REAL,
    estimated_slippage REAL,
    net_edge REAL,
    confidence REAL,
    size_usd REAL,
    status TEXT,
    reason TEXT,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS paper_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT DEFAULT CURRENT_TIMESTAMP,
    signal_id INTEGER,
    market_id TEXT,
    token_id TEXT,
    side TEXT,
    limit_price REAL,
    requested_size_usd REAL,
    fill_price REAL,
    filled_size_usd REAL,
    status TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS paper_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opened_at TEXT DEFAULT CURRENT_TIMESTAMP,
    closed_at TEXT,
    market_id TEXT,
    token_id TEXT,
    side TEXT,
    shares REAL,
    avg_entry REAL,
    mark_price REAL,
    realized_pnl REAL,
    unrealized_pnl REAL,
    status TEXT
);

CREATE TABLE IF NOT EXISTS performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT DEFAULT CURRENT_TIMESTAMP,
    strategy TEXT,
    pnl REAL,
    roi REAL,
    drawdown REAL,
    trade_count INTEGER,
    notes TEXT
);

