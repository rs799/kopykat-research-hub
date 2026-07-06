# Polymarket Algo Framework

Research-first framework for a Polymarket prediction-market algorithm.

This starter repo is **paper-trading only** by design. It gives us the structure for market ingestion, order-book snapshots, wallet ingestion, wallet scoring, signal generation, risk filtering, simulated orders, and a monitoring dashboard.

It does **not** place live orders.

## Architecture

```text
Gamma API / CLOB API / Data API
        ↓
Collectors (markets, order books, wallet trades/positions, closed positions)
        ↓
SQLite/PostgreSQL database
        ↓
Feature engine (resolved PnL, CLV, drawdown, niche, recency, liquidity)
        ↓
Wallet scoring + fair-value placeholder
        ↓
Signal engine
        ↓
Risk engine
        ↓
Paper execution
        ↓
Dashboard + logs
```

## Setup

```bash
cd polymarket_algo_framework
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python -m polyalgo.cli init-db
```

Running `init-db` again later (e.g. after pulling an update that adds a migration) is always safe - it runs every `sql/*.sql` file in order and only adds new columns/tables that don't exist yet. It never drops or overwrites existing data.

## Commands

Fetch market metadata:

```bash
python -m polyalgo.cli fetch-markets --limit 100
```

Snapshot order books for stored markets:

```bash
python -m polyalgo.cli snapshot-books --limit 20
```

Ingest one wallet's trades and OPEN positions:

```bash
python -m polyalgo.cli ingest-wallet --wallet 0x0000000000000000000000000000000000000000
```

Ingest that wallet's RESOLVED/closed positions (realized PnL - kept in a separate table from open positions, see "Wallet scoring" below):

```bash
python -m polyalgo.cli ingest-closed-positions --wallet 0x0000000000000000000000000000000000000000
```

Compute closing-line value (CLV) for that wallet's BUY trades, comparing entry price to price 1h / 6h / 24h / at-close later:

```bash
python -m polyalgo.cli compute-clv --wallet 0x0000000000000000000000000000000000000000
```

Score wallets:

```bash
python -m polyalgo.cli score-wallets
```

Track a wallet (public address monitoring only - never private key access):

```bash
python -m polyalgo.cli add-wallet --wallet 0x... --label "some wallet" --source manual
python -m polyalgo.cli list-wallets
python -m polyalgo.cli remove-wallet --wallet 0x...
```

Ingest a tracked wallet's FULL activity feed (TRADE, SPLIT, MERGE, REDEEM - not just /trades):

```bash
python -m polyalgo.cli ingest-wallet-activity --wallet 0x...
python -m polyalgo.cli ingest-tracked-wallets-activity   # runs it for every active tracked wallet
python -m polyalgo.cli show-wallet-activity --wallet 0x... --limit 50
python -m polyalgo.cli debug-wallet-activity --wallet 0x... --show-raw-keys
```

Generate placeholder paper signals:

```bash
python -m polyalgo.cli generate-signals --size 25
```

Paper-fill latest candidate signals:

```bash
python -m polyalgo.cli paper-execute --bankroll 1000 --limit 20
```

Show latest candidate signals:

```bash
python -m polyalgo.cli show-signals
```

Run dashboard:

```bash
streamlit run src/polyalgo/dashboard/app.py
```

The dashboard has a wallet leaderboard, a per-wallet detail view with a full score component breakdown (weight / raw score / contribution / what data was used, for every component), resolved closed positions, per-trade CLV samples, candidate + rejected signals, and paper orders/positions.

## Wallet scoring

`score-wallets` computes, per wallet:

```text
WalletScore =
    20 x Bayesian_ROI_score            (REALIZED ROI only - never unrealized)
  + 15 x Closing_Line_Value_score
  + 15 x Niche_Specialization_score
  + 10 x Sample_Size_score
  + 10 x Drawdown_Control_score
  + 10 x Liquidity_Adjusted_PnL_score
  + 10 x Timing_Edge_score
  +  5 x Exit_Quality_score
  +  5 x Recency_score
  - penalties (low sample size, one-hit-wonder, negative CLV, concentration risk)
```

Key rule: **unrealized (open-position) PnL is never used in scoring.** It's stored and shown in the dashboard for context, but a wallet only gets credit for performance in markets that have actually resolved. Wallets with fewer than 20 resolved trades are always classified `insufficient_sample`, regardless of how good their raw numbers look.

Every component records a note explaining exactly what data it used, or says explicitly that data was missing/insufficient and the component was left neutral (0.5) - nothing is silently guessed. See the "Wallet detail" tab in the dashboard, or `wallet_scores.component_json` directly.

`exit_quality_score` is currently always neutral (0.5) - it requires FIFO entry/exit trade matching that isn't built yet. See the TODO in `src/polyalgo/scoring/wallets.py`.

## Wallet lifecycle tracking

`ingest/wallets.py` only pulls `/trades` (BUY/SELL fills). A wallet can also exit a position via:

- **MERGE** - converting matched YES+NO shares back to USDC (a real exit that never shows up as a SELL)
- **REDEEM** - claiming USDC after a market resolves
- **SPLIT** - locking USDC to mint a full YES+NO set (position construction, not a directional bet)

If we only watched `/trades`, we'd think a wallet was still holding a position it had already exited via MERGE or REDEEM. `ingest-wallet-activity` pulls the full activity feed and normalizes every record into `wallet_lifecycle_events` (`TRADE_BUY`, `TRADE_SELL`, `MERGE`, `REDEEM`, `SPLIT`, or `UNKNOWN` for anything unrecognized - stored, never dropped).

**This is lifecycle information only right now - it does not feed wallet scoring or signal generation yet.** MERGE/REDEEM/SPLIT events are visible in the dashboard so you can see a wallet's true exit behavior, but wiring them into scoring/signals is a deliberately separate future task.

Every raw activity record is stored in `wallet_activity_raw` with `raw_json` intact, `parsed_ok`, and `parse_warning` - nothing is ever silently dropped, even when a record doesn't match the expected shape.

## KopyKat API bridge

A FastAPI app bridges this backend to the KopyKat frontend (a separate Lovable/React repo currently running on mock data). It matches KopyKat's `src/mock/api.ts` contract exactly (including camelCase field names) so that repo can later swap mock calls for real `fetch()` calls with no changes to any page component.

Run it:

```bash
uvicorn polyalgo.api.main:app --reload --port 8000
```

This matches the backend URL already hardcoded as the default in KopyKat's Settings page (`http://localhost:8000`). CORS is enabled for `http://localhost:5173`, `http://localhost:3000`, and `*.lovable.app` / `*.lovableproject.com` preview origins.

**Real, DB-backed endpoints:** `/api/wallets` (GET/POST/DELETE), `/api/data-health`, `/api/paper-simulation`, `/api/overview` (partially - see below), `/api/health`.

**Honestly empty/placeholder endpoints** (the underlying feature isn't built yet, so these return `[]` or `404` rather than fabricated data): `/api/niches`, `/api/niches/{niche}/wallet-discovery`, `/api/niches/{niche}/wallet-rankings`, `/api/consensus-alerts`, `/api/alerts/{id}`, `/api/backtests`. `/api/overview`'s `activeNiches`/`consensusAlerts`/`rejectedAlerts` fields are always `0` for the same reason.

Known mapping caveats (see docstrings in `src/polyalgo/api/routes/` for detail):
- `Wallet.clv` currently returns our 0..1 normalized CLV *score*, not a raw side-adjusted CLV value like KopyKat's mock data uses - different units, needs reconciling later.
- `Wallet.status` maps our `classification` onto KopyKat's `qualified/watch/rejected/suspicious` enum; we have no "suspicious" (Sybil/wash-trade) detection, so that value is never produced.
- `PaperSimulation.balance` is always `0` - there's no persisted starting-bankroll concept in the schema yet.

## Strategy philosophy

The first live-worthy version should only consider a signal when:

```text
wallet score is high
sample size is sufficient
CLV is positive
market spread is tight
visible liquidity is adequate
price has not already moved too far
resolution risk is not high
net edge after costs remains positive
```

## What is already included

```text
src/polyalgo/
  clients/       Polymarket REST/WebSocket clients
  ingest/        Market, order-book, wallet, closed-position, and activity/lifecycle collectors
  scoring/       Wallet scoring, resolved-PnL stats, CLV, lifecycle classification, Bayesian shrinkage
  strategy/      Signals, risk, paper trading, backtest skeleton
  execution/     Live order manager placeholder (raises unless TRADING_MODE=live)
  dashboard/     Streamlit dashboard
  cli.py         Command-line interface
sql/
  001_init.sql                           Base schema
  002_resolved_and_clv.sql               Closed positions + per-trade CLV tables
  003_tracked_wallets_and_activity.sql   Tracked wallets + full activity/lifecycle tables
tests/
  Unit + integration tests (pure functions, CLV, resolved-PnL, wallet scoring, activity parsing, lifecycle, tracked wallets)
```

## What still needs to be added before any live money

- niche classification (tagging markets/wallets into crypto/sports/macro/tech/global) - the API bridge's niche/ranking/consensus endpoints are stubs until this exists,
- consensus alert engine (multiple top wallets aligning on the same market/outcome),
- reconcile `Wallet.clv` in the API to use a raw side-adjusted CLV value (from `scoring/clv.py`) instead of the normalized 0..1 score, to match KopyKat's expected units,
- verify the closed-positions, prices-history, AND activity field mappings against the LIVE Data/CLOB API (this build environment has no network access to polymarket.com, so none of `ingest/closed_positions.py`, `scoring/clv.py`, or `ingest/activity.py` have been run against real responses - see the docstrings in those files),
- wire MERGE/REDEEM/SPLIT lifecycle events into scoring and signal generation (currently lifecycle-only, deliberately not used for signals yet),
- FIFO entry/exit trade matching, to make `exit_quality_score` real instead of neutral,
- historical order-book archive with a timestamp-indexed lookup, so `liquidity_score` can match depth *at trade time* instead of "whatever depth snapshots happen to exist",
- proper slippage model (current paper execution should already avoid midpoint fantasy fills - verify this against `strategy/paper.py`),
- niche-specific fair-value models,
- out-of-sample backtesting,
- 30-60 days paper trading,
- jurisdiction and platform-policy checks,
- Postgres portability pass (schema currently uses SQLite's `INTEGER PRIMARY KEY AUTOINCREMENT` and some `INSERT OR REPLACE` statements; these are SQLite-specific and would need updating - `SERIAL`/`IDENTITY` + `ON CONFLICT` - to run against the Postgres service in `docker-compose.yml`),
- market ingestion pagination (current `fetch-markets` only pulls a single page),
- live execution module using CLOB V2 SDK only after all of the above.

## Recommended build order

1. Make market ingestion stable (pagination, dedup).
2. Build reliable `condition_id <-> token_id <-> event` mapping.
3. Archive order-book snapshots on a schedule.
4. Ingest wallet trades, open positions, AND resolved/closed positions.
5. Compute CLV and build wallet scoring (this is what this update focused on).
6. Paper trade wallet-following signals.
7. Add historical backtesting.
8. Add niche-specific fair-value models.
9. Add relative-value scanner.
10. Only after long paper testing, design live execution.
