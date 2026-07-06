from __future__ import annotations

"""
FastAPI bridge between the Python research backend and the KopyKat frontend
(kopykat-research-hub, a Lovable-built React app currently running on mock
data).

Run locally with:
    uvicorn polyalgo.api.main:app --reload --port 8000

This matches the backend URL already hardcoded as the default in KopyKat's
Settings page (http://localhost:8000).

Hard rules that apply to every route in this app (see project-level rules):
  - no live order placement, no private key handling
  - TRADING_MODE stays "paper"
  - never fabricate data for an unimplemented feature - return empty
    lists / clear placeholder statuses instead (see each route module's
    docstring for what's real vs. not-yet-built)
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.engine import Engine

from polyalgo.api.deps import get_engine_dependency
from polyalgo.api.routes import alerts, backtests, data_health, niches, overview, paper, wallets
from polyalgo.api.schemas import HealthResponse
from polyalgo.config import get_settings

app = FastAPI(
    title="Polymarket Algo Framework - KopyKat API Bridge",
    description="Research-only, paper-trading-first backend for the KopyKat wallet-intelligence dashboard.",
    version="0.1.0",
)

# KopyKat runs locally via Vite (default 5173) or occasionally CRA-style
# tooling (3000). Lovable's hosted preview origin varies per project, so we
# also allow *.lovable.app / *.lovableproject.com via regex - adjust this if
# your actual preview origin doesn't match.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_origin_regex=r"https://.*\.(lovable\.app|lovableproject\.com)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router)
app.include_router(niches.router)
app.include_router(wallets.router)
app.include_router(alerts.router)
app.include_router(data_health.router)
app.include_router(paper.router)
app.include_router(backtests.router)


@app.get("/api/health", response_model=HealthResponse)
def health(engine: Engine = Depends(get_engine_dependency)) -> HealthResponse:
    settings = get_settings()
    database_connected = True
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        database_connected = False

    return HealthResponse(
        status="ok",
        mode=settings.trading_mode,
        backend="local",
        live_trading_enabled=(settings.trading_mode == "live"),
        database_connected=database_connected,
    )
