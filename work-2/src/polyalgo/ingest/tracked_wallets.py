from __future__ import annotations

"""
Tracked wallets: the list of wallet addresses we intentionally monitor.

This is public-address monitoring only - reading a wallet's public trade
history via the Data API. It is not private wallet access of any kind, and
never involves a private key.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from polyalgo.db import get_engine

VALID_SOURCES = {
    "manual",
    "leaderboard",
    "market_holder",
    "polysyncer_style",
    "article",
    "discovered_from_market",
}


def add_wallet(
    wallet: str,
    label: str | None = None,
    source: str = "manual",
    notes: str | None = None,
    engine: Engine | None = None,
) -> dict:
    """Add a wallet to the tracked list, or reactivate/update it if it's
    already there (upsert by wallet_address)."""
    engine = engine or get_engine()
    wallet = wallet.lower()

    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM tracked_wallets WHERE lower(wallet_address) = :wallet"),
            {"wallet": wallet},
        ).mappings().first()

        if existing:
            conn.execute(
                text("""
                    UPDATE tracked_wallets
                    SET label = COALESCE(:label, label),
                        source = :source,
                        notes = COALESCE(:notes, notes),
                        is_active = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE lower(wallet_address) = :wallet
                """),
                {"wallet": wallet, "label": label, "source": source, "notes": notes},
            )
            return {"wallet": wallet, "status": "updated"}

        conn.execute(
            text("""
                INSERT INTO tracked_wallets (wallet_address, label, source, notes, is_active)
                VALUES (:wallet, :label, :source, :notes, 1)
            """),
            {"wallet": wallet, "label": label, "source": source, "notes": notes},
        )
        return {"wallet": wallet, "status": "added"}


def remove_wallet(wallet: str, engine: Engine | None = None) -> dict:
    """Soft-delete: mark inactive rather than deleting, so history/labels
    aren't lost if the wallet is re-added later."""
    engine = engine or get_engine()
    wallet = wallet.lower()

    with engine.begin() as conn:
        result = conn.execute(
            text("""
                UPDATE tracked_wallets
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE lower(wallet_address) = :wallet
            """),
            {"wallet": wallet},
        )

    if result.rowcount == 0:
        return {"wallet": wallet, "status": "not_found"}
    return {"wallet": wallet, "status": "removed"}


def list_wallets(active_only: bool = True, engine: Engine | None = None) -> list[dict]:
    engine = engine or get_engine()
    query = """
        SELECT t.wallet_address, t.label, t.source, t.notes, t.is_active,
               t.created_at, t.updated_at, t.last_ingested_at,
               s.final_score, s.classification, s.resolved_trade_count
        FROM tracked_wallets t
        LEFT JOIN wallet_scores s ON lower(s.wallet) = lower(t.wallet_address)
    """
    if active_only:
        query += " WHERE t.is_active = 1"
    query += " ORDER BY t.created_at DESC"

    with engine.begin() as conn:
        rows = conn.execute(text(query)).mappings().all()
    return [dict(r) for r in rows]


def mark_ingested(wallet: str, engine: Engine | None = None) -> None:
    engine = engine or get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE tracked_wallets
                SET last_ingested_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE lower(wallet_address) = lower(:wallet)
            """),
            {"wallet": wallet},
        )
