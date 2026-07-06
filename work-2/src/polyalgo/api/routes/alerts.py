from __future__ import annotations

"""
The consensus alert engine (detecting when multiple top-ranked wallets in a
niche align on the same market/outcome within a time window) is not
implemented. It depends on niche classification and per-niche wallet
rankings, neither of which exist yet - see routes/niches.py.

Per the hard rule "do not fake real backend results", these endpoints
return an empty list / 404 rather than synthetic alerts.
"""

from fastapi import APIRouter, HTTPException

from polyalgo.api.schemas import ConsensusAlert

router = APIRouter()


@router.get("/api/consensus-alerts", response_model=list[ConsensusAlert])
def list_consensus_alerts() -> list[ConsensusAlert]:
    # TODO: implement the consensus engine (CLAUDE_UPDATE_KOPYKAT_API_BRIDGE.md
    # section 10, item 5) once niche classification + rankings exist.
    return []


@router.get("/api/alerts/{alert_id}", response_model=ConsensusAlert)
def get_alert(alert_id: str) -> ConsensusAlert:
    # No alerts exist yet since the consensus engine isn't built - every
    # lookup is a real 404, not a fabricated "empty" alert object, so the
    # frontend can distinguish "not built yet" from "built but no data".
    raise HTTPException(
        status_code=404,
        detail=f"Alert {alert_id} not found - the consensus engine is not implemented yet",
    )
