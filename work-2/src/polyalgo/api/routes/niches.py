from __future__ import annotations

"""
Niche classification (tagging markets/wallets into crypto/sports/macro/tech/
global, matching KopyKat's NicheKey type) is not implemented in the backend
yet. See CLAUDE_UPDATE_KOPYKAT_API_BRIDGE.md section 10, item 1 - it's the
very next backend task after this API bridge.

`markets.category` exists in the schema and holds something (Polymarket's
own category strings), but it has NOT been verified to line up with
KopyKat's five niche buckets, and mapping one onto the other without
checking would be exactly the kind of guessing this project avoids. So
these endpoints return empty lists / "not_started" rather than inventing a
category-to-niche mapping.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Engine

from polyalgo.api.deps import get_engine_dependency
from polyalgo.api.schemas import Niche, RankedWallet, Wallet

router = APIRouter()


@router.get("/api/niches", response_model=list[Niche])
def list_niches(engine: Engine = Depends(get_engine_dependency)) -> list[Niche]:
    # TODO: once niche classification exists, return one Niche per bucket
    # with real market/wallet counts computed from the DB.
    return []


@router.get("/api/niches/{niche}/wallet-discovery", response_model=list[Wallet])
def wallet_discovery(niche: str, engine: Engine = Depends(get_engine_dependency)) -> list[Wallet]:
    # TODO: once wallets are tagged with a niche, filter wallet_scores /
    # tracked_wallets by niche and return them here.
    return []


@router.get("/api/niches/{niche}/wallet-rankings", response_model=list[RankedWallet])
def wallet_rankings(niche: str, engine: Engine = Depends(get_engine_dependency)) -> list[RankedWallet]:
    # TODO: requires per-niche wallet scoring, not just the global
    # wallet_scores table. Not implemented yet.
    return []
