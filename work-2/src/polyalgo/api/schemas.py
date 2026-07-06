from __future__ import annotations

"""
Response schemas for the KopyKat API bridge.

Field names in this file are deliberately camelCase (not the usual Python
snake_case) because they mirror KopyKat's TypeScript interfaces in
`kopykat-research-hub/src/mock/data.ts` exactly. The whole point of this
bridge is that KopyKat's `src/mock/api.ts` can later be swapped for real
`fetch()` calls with zero changes to any page component - that only works
if the JSON we return has the exact same shape (including key casing) as
the mock data does today. Deviating to snake_case here would silently break
that goal.

Every schema here corresponds 1:1 to an interface in `mock/data.ts`. If you
change a KopyKat interface, update the matching schema here too.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

CAMEL_MODEL_CONFIG = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Niches
# ---------------------------------------------------------------------------


class Niche(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    key: str
    name: str
    markets: int
    discoveredWallets: int
    qualifiedWallets: int
    avgLiquidity: Optional[float] = None
    alerts: int
    warnings: int
    status: Literal["healthy", "degraded", "stale", "not_started"]
    description: str


# ---------------------------------------------------------------------------
# Wallets
# ---------------------------------------------------------------------------


class Wallet(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    address: str
    niche: Optional[str] = None
    marketsObserved: int
    resolvedObservations: int
    realizedPnl: float
    roi: Optional[float] = None
    clv: Optional[float] = None
    sampleSize: int
    status: Literal["qualified", "watch", "rejected", "suspicious"]
    reason: str
    firstSeen: Optional[str] = None
    lastSeen: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    source: str
    nichesObserved: list[str] = Field(default_factory=list)


class RankedWalletBreakdown(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    bayesianRoi: float
    clv: float
    sampleSize: float
    drawdownControl: float
    liquidityAdj: float
    timingEdge: float
    recency: float
    penalties: float


class RankedWallet(Wallet):
    model_config = CAMEL_MODEL_CONFIG

    rank: int
    nicheScore: float
    globalScore: float
    clvScore: float
    drawdown: float
    specialty: str
    recency: float
    flags: list[str] = Field(default_factory=list)
    breakdown: RankedWalletBreakdown


class AddWalletRequest(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    address: str
    niche: Optional[str] = None


class RemoveWalletResponse(BaseModel):
    ok: bool


# ---------------------------------------------------------------------------
# Consensus alerts
# ---------------------------------------------------------------------------


class AlertWalletEntry(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    address: str
    score: float
    nicheScore: float
    observedAt: str
    observedPrice: float
    size: float
    clvHistory: float
    status: str


class AlertDisagreementEntry(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    address: str
    side: str
    size: float
    note: str


class ConsensusAlert(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    id: str
    strength: float
    niche: str
    market: str
    side: Optional[str] = None
    walletsAligned: int
    avgWalletScore: Optional[float] = None
    firstPrice: Optional[float] = None
    currentPrice: Optional[float] = None
    priceMoved: Optional[float] = None
    spread: Optional[float] = None
    liquidity: Optional[float] = None
    disagreement: int
    status: Literal["watch", "paper", "rejected", "empty"]
    reason: str
    observedAt: Optional[str] = None
    consensusScore: Optional[float] = None
    avgWalletQuality: Optional[float] = None
    suggestedMaxPrice: Optional[float] = None
    wallets: list[AlertWalletEntry] = Field(default_factory=list)
    disagreementDetail: list[AlertDisagreementEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Paper simulation
# ---------------------------------------------------------------------------


class PaperOrder(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    id: str
    time: str
    market: str
    side: str
    price: float
    size: float
    status: Literal["filled", "partial", "missed"]
    linkedAlert: Optional[str] = None


class PaperPosition(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    market: str
    side: str
    avgPrice: float
    size: float
    markPrice: Optional[float] = None
    unrealized: Optional[float] = None


class PaperSimulation(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    balance: float
    openPositions: int
    realizedPnl: float
    unrealizedPnl: float
    winRate: Optional[float] = None
    maxDrawdown: Optional[float] = None
    fillRate: Optional[float] = None
    missedFillRate: Optional[float] = None
    orders: list[PaperOrder] = Field(default_factory=list)
    positions: list[PaperPosition] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Backtests
# ---------------------------------------------------------------------------


class Backtest(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    id: str
    niche: str
    strategy: str
    roi: float
    maxDrawdown: float
    fillRate: float
    missedFillRate: float
    avgAlertStrength: float
    runs: int


# ---------------------------------------------------------------------------
# Data health
# ---------------------------------------------------------------------------


class DataHealthEndpoint(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    name: str
    status: Literal["ok", "degraded", "down", "no_data"]
    lastIngestion: Optional[str] = None


class Warning(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    timestamp: Optional[str] = None
    endpoint: str
    wallet: Optional[str] = None
    severity: Literal["low", "med", "high"]
    warning: str
    rawField: Optional[str] = None
    parsedField: Optional[str] = None
    message: str


class DataHealth(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    endpoints: list[DataHealthEndpoint] = Field(default_factory=list)
    rawRows: int
    lifecycleEvents: int
    unresolvedIssues: int
    warnings: list[Warning] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


class Overview(BaseModel):
    model_config = CAMEL_MODEL_CONFIG

    activeNiches: int
    discoveredWallets: int
    qualifiedWallets: int
    consensusAlerts: int
    rejectedAlerts: int
    paperPnl: float
    parserWarnings: int
    backendStatus: str
    mode: str


# ---------------------------------------------------------------------------
# Health (operational endpoint, not part of the KopyKat mock contract)
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    mode: str
    backend: str
    live_trading_enabled: bool
    database_connected: bool
