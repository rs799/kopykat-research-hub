from __future__ import annotations

"""
Wallets endpoints. This is the most "real" part of the bridge - it reads
from wallet_scores and tracked_wallets, which are both populated by the
existing ingestion/scoring pipeline.

Mapping notes (read before trusting these fields downstream):

  - `status` maps our `classification` (candidate_smart_wallet / watchlist /
    ignore / insufficient_sample) onto KopyKat's Wallet.status enum
    (qualified / watch / rejected / suspicious). We have no "suspicious"
    (Sybil/wash-trade) detection yet, so that bucket is never produced by
    this backend - see the TODO below.
  - `clv` is our 0..1 normalized CLV *score* component (from wallet_scores),
    not a raw side-adjusted price-delta CLV like KopyKat's mock data uses
    (which ranges roughly -0.03..0.14). These are different units. Treat
    this as a placeholder until routes are updated to pull the raw average
    from scoring/clv.py's summarize_wallet_clv() instead.
  - `niche` / `nichesObserved` are always null/empty - niche classification
    isn't implemented (see routes/niches.py).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Engine

from polyalgo.api.deps import get_engine_dependency
from polyalgo.api.schemas import AddWalletRequest, RemoveWalletResponse, Wallet
from polyalgo.ingest.tracked_wallets import add_wallet as add_tracked_wallet
from polyalgo.ingest.tracked_wallets import remove_wallet as remove_tracked_wallet

router = APIRouter()

# TODO: no Sybil-cluster / wash-trade / bot-timing detection exists yet, so
# "suspicious" is never produced. When that detection is built, wire it in
# here rather than guessing from existing fields.
_CLASSIFICATION_TO_STATUS = {
    "candidate_smart_wallet": "qualified",
    "watchlist": "watch",
    "ignore": "rejected",
    "insufficient_sample": "watch",
}


def _status_for(classification: str | None) -> str:
    return _CLASSIFICATION_TO_STATUS.get(classification or "", "watch")


def _row_to_wallet(row: dict) -> Wallet:
    return Wallet(
        address=row["wallet_address"],
        niche=None,
        marketsObserved=row.get("markets_observed") or 0,
        resolvedObservations=row.get("resolved_trade_count") or 0,
        realizedPnl=row.get("realized_pnl") or 0.0,
        roi=row.get("realized_roi"),
        clv=row.get("clv_score"),
        sampleSize=row.get("resolved_trade_count") or 0,
        status=_status_for(row.get("classification")),
        reason=row.get("notes") or ("Tracked, not yet scored" if row.get("classification") is None else ""),
        firstSeen=row.get("first_seen"),
        lastSeen=row.get("last_seen"),
        tags=[],
        source=row.get("source") or "unknown",
        nichesObserved=[],
    )


@router.get("/api/wallets", response_model=list[Wallet])
def list_wallets(engine: Engine = Depends(get_engine_dependency)) -> list[Wallet]:
    """Union of everything we know about a wallet: tracked_wallets (source,
    label) left-joined with wallet_scores (performance), plus wallets that
    have been scored but were never explicitly tracked. Market count and
    first/last-seen are derived from wallet_trades.

    Uses a UNION rather than a FULL OUTER JOIN so this runs the same way on
    SQLite and Postgres.
    """
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    t.wallet_address AS wallet_address,
                    t.source AS source,
                    s.classification AS classification,
                    s.notes AS notes,
                    s.realized_pnl AS realized_pnl,
                    s.realized_roi AS realized_roi,
                    s.resolved_trade_count AS resolved_trade_count,
                    s.clv_score AS clv_score,
                    (SELECT COUNT(DISTINCT market_id) FROM wallet_trades wt
                     WHERE lower(wt.wallet) = lower(t.wallet_address)) AS markets_observed,
                    (SELECT MIN(ts) FROM wallet_trades wt
                     WHERE lower(wt.wallet) = lower(t.wallet_address)) AS first_seen,
                    (SELECT MAX(ts) FROM wallet_trades wt
                     WHERE lower(wt.wallet) = lower(t.wallet_address)) AS last_seen
                FROM tracked_wallets t
                LEFT JOIN wallet_scores s ON lower(s.wallet) = lower(t.wallet_address)
                WHERE t.is_active = 1

                UNION

                SELECT
                    s.wallet AS wallet_address,
                    NULL AS source,
                    s.classification AS classification,
                    s.notes AS notes,
                    s.realized_pnl AS realized_pnl,
                    s.realized_roi AS realized_roi,
                    s.resolved_trade_count AS resolved_trade_count,
                    s.clv_score AS clv_score,
                    (SELECT COUNT(DISTINCT market_id) FROM wallet_trades wt
                     WHERE lower(wt.wallet) = lower(s.wallet)) AS markets_observed,
                    (SELECT MIN(ts) FROM wallet_trades wt
                     WHERE lower(wt.wallet) = lower(s.wallet)) AS first_seen,
                    (SELECT MAX(ts) FROM wallet_trades wt
                     WHERE lower(wt.wallet) = lower(s.wallet)) AS last_seen
                FROM wallet_scores s
                WHERE lower(s.wallet) NOT IN (SELECT lower(wallet_address) FROM tracked_wallets)
                -- Note: this excludes a wallet from BOTH branches once it has ever
                -- been tracked and then removed (soft-deleted), even if it still has
                -- a wallet_scores row. This matches the frontend's expectation that
                -- DELETE /api/wallets/{wallet} makes it disappear from the wallet
                -- database view - re-add it with POST /api/wallets to see it again.
            """)
        ).mappings().all()

    return [_row_to_wallet(dict(r)) for r in rows]


@router.post("/api/wallets", response_model=Wallet)
def add_wallet(payload: AddWalletRequest, engine: Engine = Depends(get_engine_dependency)) -> Wallet:
    # TODO: tracked_wallets has no niche column yet (niche classification
    # isn't implemented - see routes/niches.py). We stash the requested
    # niche in `notes` as a breadcrumb so it isn't silently discarded, but
    # this is NOT the same as real niche tagging.
    notes = f"niche(requested)={payload.niche}" if payload.niche else None
    add_tracked_wallet(payload.address, source="manual", notes=notes, engine=engine)

    return Wallet(
        address=payload.address.lower(),
        niche=payload.niche,
        marketsObserved=0,
        resolvedObservations=0,
        realizedPnl=0.0,
        roi=None,
        clv=None,
        sampleSize=0,
        status="watch",
        reason="Manually added, awaiting observations",
        firstSeen=None,
        lastSeen=None,
        tags=["manual"],
        source="manual",
        nichesObserved=[payload.niche] if payload.niche else [],
    )


@router.delete("/api/wallets/{wallet}", response_model=RemoveWalletResponse)
def remove_wallet(wallet: str, engine: Engine = Depends(get_engine_dependency)) -> RemoveWalletResponse:
    result = remove_tracked_wallet(wallet, engine=engine)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=f"Wallet {wallet} is not tracked")
    return RemoveWalletResponse(ok=True)
