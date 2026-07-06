from __future__ import annotations

"""
Streamlit dashboard for the Polymarket algo framework.

This is a research/monitoring tool only - it never places orders. Its main
job is to make wallet scoring HONEST and INSPECTABLE: for every wallet you
can see exactly which resolved trades, CLV samples, and score components
produced its final number, and where data was missing rather than guessed.
"""

import json

import pandas as pd
import streamlit as st
from sqlalchemy import text
from polyalgo.db import get_engine

st.set_page_config(page_title="Polymarket Algo Framework", layout="wide")
st.title("Polymarket Algo Framework")
st.caption("Research / paper-trading only. No live orders are ever placed from this app.")

engine = get_engine()


def load_df(query: str, params: dict | None = None) -> pd.DataFrame:
    try:
        with engine.begin() as conn:
            return pd.read_sql_query(text(query), conn, params=params or {})
    except Exception as exc:
        st.error(f"Query failed: {exc}")
        return pd.DataFrame()


tab_overview, tab_wallets, tab_activity, tab_signals, tab_paper = st.tabs(
    [
        "Overview",
        "Wallet leaderboard & detail",
        "Tracked wallets & activity",
        "Signals (candidate + rejected)",
        "Paper trading",
    ]
)

# ---------------------------------------------------------------------------
# Overview tab
# ---------------------------------------------------------------------------
with tab_overview:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        markets = load_df("SELECT COUNT(*) AS n FROM markets")
        st.metric("Markets", int(markets["n"].iloc[0]) if not markets.empty else 0)

    with col2:
        books = load_df("SELECT COUNT(*) AS n FROM orderbook_snapshots")
        st.metric("Book snapshots", int(books["n"].iloc[0]) if not books.empty else 0)

    with col3:
        wallets_scored = load_df("SELECT COUNT(*) AS n FROM wallet_scores")
        st.metric("Wallets scored", int(wallets_scored["n"].iloc[0]) if not wallets_scored.empty else 0)

    with col4:
        signals = load_df("SELECT COUNT(*) AS n FROM signals WHERE status='candidate'")
        st.metric("Candidate signals", int(signals["n"].iloc[0]) if not signals.empty else 0)

    st.subheader("Latest markets")
    st.dataframe(
        load_df("""
            SELECT market_id, question, category, active, closed, enable_orderbook, end_date
            FROM markets
            ORDER BY updated_at DESC
            LIMIT 50
        """),
        use_container_width=True,
    )

    st.subheader("Latest order books")
    st.dataframe(
        load_df("""
            SELECT ts, market_id, token_id, best_bid, best_ask, midpoint, spread, depth_1c, depth_3c
            FROM orderbook_snapshots
            ORDER BY ts DESC
            LIMIT 100
        """),
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Wallet leaderboard & detail tab
# ---------------------------------------------------------------------------
with tab_wallets:
    st.subheader("Wallet leaderboard")
    st.caption(
        "Ranked by final_score, which is based ONLY on resolved-market performance "
        "(realized PnL, CLV, drawdown, niche skill, etc). Unrealized/open-position "
        "PnL is shown separately and never affects this ranking."
    )

    leaderboard = load_df("""
        SELECT wallet, classification, final_score, resolved_trade_count, realized_pnl,
               realized_roi, clv_score, clv_sample_size, unrealized_pnl, open_position_count,
               updated_at
        FROM wallet_scores
        ORDER BY final_score DESC
        LIMIT 200
    """)
    st.dataframe(leaderboard, use_container_width=True)

    st.subheader("Wallet detail")
    all_wallets = load_df("SELECT wallet FROM wallet_scores ORDER BY final_score DESC")

    if all_wallets.empty:
        st.info("No wallets scored yet. Run `polyalgo score-wallets` after ingesting some wallets.")
    else:
        selected_wallet = st.selectbox("Select a wallet", all_wallets["wallet"].tolist())

        detail = load_df(
            "SELECT * FROM wallet_scores WHERE wallet = :wallet", {"wallet": selected_wallet}
        )

        if not detail.empty:
            row = detail.iloc[0]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Final score", f"{row['final_score']:.1f}", row["classification"])
            c2.metric("Resolved trades", int(row["resolved_trade_count"] or 0))
            c3.metric("Realized PnL", f"${row['realized_pnl']:.2f}" if row["realized_pnl"] is not None else "n/a")
            c4.metric(
                "Realized ROI",
                f"{row['realized_roi']:.3f}" if row["realized_roi"] is not None else "n/a",
            )

            st.warning(
                f"Unrealized (open-position) PnL: ${row['unrealized_pnl']:.2f} across "
                f"{int(row['open_position_count'] or 0)} open positions. "
                "This is NOT included in the score above - open positions can still reverse."
            )

            st.markdown("**Notes:** " + str(row.get("notes") or ""))

            st.subheader("Score component breakdown")
            try:
                breakdown = json.loads(row["component_json"] or "{}")
            except (TypeError, json.JSONDecodeError):
                breakdown = {}

            components = breakdown.get("components", [])
            if components:
                comp_df = pd.DataFrame(components)
                comp_df = comp_df.rename(
                    columns={
                        "name": "Component",
                        "weight": "Weight",
                        "raw_score": "Raw score (0-1)",
                        "contribution": "Contribution (pts)",
                        "note": "What data was used",
                    }
                )
                st.dataframe(comp_df, use_container_width=True)
            else:
                st.info("No component breakdown stored for this wallet yet.")

            penalties = breakdown.get("penalties", [])
            if penalties:
                st.subheader("Penalties applied")
                pen_df = pd.DataFrame(penalties).rename(
                    columns={"name": "Penalty", "points": "Points", "note": "Why"}
                )
                st.dataframe(pen_df, use_container_width=True)
            else:
                st.caption("No penalties applied to this wallet.")

            st.subheader("Resolved (closed) positions")
            st.dataframe(
                load_df(
                    """
                    SELECT market_id, token_id, outcome, size, avg_price, realized_pnl,
                           realized_pnl_pct, resolved_price, closed_ts
                    FROM wallet_closed_positions
                    WHERE lower(wallet) = lower(:wallet)
                    ORDER BY closed_ts DESC
                    LIMIT 100
                    """,
                    {"wallet": selected_wallet},
                ),
                use_container_width=True,
            )

            st.subheader("Per-trade CLV samples")
            st.caption(
                "Only BUY (position-opening) trades get a CLV calculation. "
                "missing_* = True means price-history data wasn't available at that horizon - never guessed."
            )
            st.dataframe(
                load_df(
                    """
                    SELECT market_id, token_id, entry_price, entry_ts,
                           clv_1h, clv_6h, clv_24h, clv_close,
                           missing_1h, missing_6h, missing_24h, missing_close
                    FROM wallet_trade_clv
                    WHERE lower(wallet) = lower(:wallet)
                    ORDER BY entry_ts DESC
                    LIMIT 100
                    """,
                    {"wallet": selected_wallet},
                ),
                use_container_width=True,
            )

            st.subheader("Open (unrealized) positions - for context only")
            st.dataframe(
                load_df(
                    """
                    SELECT market_id, token_id, outcome, size, avg_price, cur_price,
                           cash_pnl, percent_pnl
                    FROM wallet_positions
                    WHERE lower(wallet) = lower(:wallet)
                    ORDER BY ts DESC
                    LIMIT 100
                    """,
                    {"wallet": selected_wallet},
                ),
                use_container_width=True,
            )

# ---------------------------------------------------------------------------
# Tracked wallets & activity tab
# ---------------------------------------------------------------------------
with tab_activity:
    st.subheader("Tracked wallets")
    st.caption(
        "Wallets we're intentionally monitoring (public addresses only - never private key access). "
        "Add wallets with `polyalgo add-wallet --wallet 0x... --label ... --source ...`."
    )

    tracked = load_df("""
        SELECT t.wallet_address, t.label, t.source, t.is_active, t.last_ingested_at,
               s.final_score, s.classification, s.resolved_trade_count,
               (SELECT COUNT(*) FROM wallet_activity_raw a WHERE lower(a.wallet_address) = lower(t.wallet_address)) AS activity_rows,
               (SELECT COUNT(*) FROM wallet_lifecycle_events e WHERE lower(e.wallet_address) = lower(t.wallet_address)) AS lifecycle_events,
               (SELECT COUNT(*) FROM wallet_activity_raw a WHERE lower(a.wallet_address) = lower(t.wallet_address) AND a.parsed_ok = 0) AS parser_warnings
        FROM tracked_wallets t
        LEFT JOIN wallet_scores s ON lower(s.wallet) = lower(t.wallet_address)
        ORDER BY t.created_at DESC
    """)
    st.dataframe(tracked, use_container_width=True)

    if tracked.empty:
        st.info("No tracked wallets yet.")
    else:
        st.subheader("Wallet activity detail")
        selected = st.selectbox("Select a tracked wallet", tracked["wallet_address"].tolist(), key="activity_wallet")

        st.markdown("**Latest lifecycle event per type**")
        latest_by_type = load_df(
            """
            SELECT event_type, MAX(timestamp) AS latest_ts
            FROM wallet_lifecycle_events
            WHERE lower(wallet_address) = lower(:wallet)
            GROUP BY event_type
            """,
            {"wallet": selected},
        )
        st.dataframe(latest_by_type, use_container_width=True)

        st.markdown("**Lifecycle events**")
        st.caption(
            "TRADE_BUY/TRADE_SELL come from /trades-style activity. MERGE/REDEEM/SPLIT are lifecycle-only "
            "right now - NOT used to generate trading signals yet (see interpretation column)."
        )
        st.dataframe(
            load_df(
                """
                SELECT timestamp, event_type, token_id, side, size, price, usdc_size, interpretation
                FROM wallet_lifecycle_events
                WHERE lower(wallet_address) = lower(:wallet)
                ORDER BY timestamp DESC
                LIMIT 200
                """,
                {"wallet": selected},
            ),
            use_container_width=True,
        )

        st.markdown("**Parser warnings (raw activity rows that didn't fully parse)**")
        warnings_df = load_df(
            """
            SELECT activity_type, timestamp, parse_warning, raw_json
            FROM wallet_activity_raw
            WHERE lower(wallet_address) = lower(:wallet) AND parsed_ok = 0
            ORDER BY created_at DESC
            LIMIT 100
            """,
            {"wallet": selected},
        )
        if warnings_df.empty:
            st.caption("No parser warnings for this wallet.")
        else:
            st.dataframe(warnings_df, use_container_width=True)

# ---------------------------------------------------------------------------
# Signals tab
# ---------------------------------------------------------------------------
with tab_signals:
    st.subheader("Candidate signals")
    st.dataframe(
        load_df("""
            SELECT ts, market_id, token_id, strategy, side, entry_price, fair_probability,
                   gross_edge, estimated_fee, estimated_slippage, net_edge, confidence, size_usd, reason
            FROM signals
            WHERE status = 'candidate'
            ORDER BY ts DESC
            LIMIT 200
        """),
        use_container_width=True,
    )

    st.subheader("Rejected signals (with reasons)")
    st.caption("Signals that failed a filter. Reviewing WHY signals were rejected matters as much as the ones accepted.")
    st.dataframe(
        load_df("""
            SELECT ts, market_id, token_id, strategy, side, entry_price, net_edge, reason
            FROM signals
            WHERE status != 'candidate'
            ORDER BY ts DESC
            LIMIT 200
        """),
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Paper trading tab
# ---------------------------------------------------------------------------
with tab_paper:
    st.subheader("Paper orders")
    st.dataframe(
        load_df("""
            SELECT ts, market_id, token_id, side, limit_price, requested_size_usd,
                   fill_price, filled_size_usd, status, reason
            FROM paper_orders
            ORDER BY ts DESC
            LIMIT 200
        """),
        use_container_width=True,
    )

    st.subheader("Paper positions")
    st.dataframe(
        load_df("""
            SELECT opened_at, closed_at, market_id, token_id, side, shares, avg_entry,
                   mark_price, realized_pnl, unrealized_pnl, status
            FROM paper_positions
            ORDER BY opened_at DESC
            LIMIT 200
        """),
        use_container_width=True,
    )
