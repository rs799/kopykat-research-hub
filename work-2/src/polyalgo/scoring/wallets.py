from __future__ import annotations

"""
Wallet scoring.

Target formula (see CLAUDE_POLYMARKET_ALGO_CONTEXT.md section 8):

    WalletScore =
        20 x Bayesian_ROI_score            (realized ROI only)
      + 15 x Closing_Line_Value_score
      + 15 x Niche_Specialization_score
      + 10 x Sample_Size_score
      + 10 x Drawdown_Control_score
      + 10 x Liquidity_Adjusted_PnL_score
      + 10 x Timing_Edge_score
      +  5 x Exit_Quality_score
      +  5 x Recency_score
      - penalties

Every component score is 0..1. Weights sum to 100, so the weighted sum before
penalties is already on a 0..100 scale.

Ground rules this module follows (see CLAUDE_POLYMARKET_ALGO_CONTEXT.md
section 13 and the task rules given alongside this build):

  - Unrealized/open-position PnL is NEVER used in Bayesian_ROI_score or any
    other component. Only resolved positions (wallet_closed_positions) count.
  - Every component records a human-readable note explaining what data was
    used, or explicitly says data was insufficient/missing and the score was
    left neutral (0.5) as a result. Nothing is silently guessed.
  - Wallets with too little resolved history are classified
    "insufficient_sample" regardless of how good their raw numbers look.
"""

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

from polyalgo.db import get_engine
from polyalgo.models import WalletScore
from polyalgo.scoring.clv import summarize_wallet_clv
from polyalgo.scoring.resolved_pnl import compute_resolved_pnl_stats, compute_unrealized_pnl_stats

# ---------------------------------------------------------------------------
# Generic helpers (pure functions - fully unit-testable without a DB)
# ---------------------------------------------------------------------------


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def bayesian_shrink(observed: float, n: int, baseline: float = 0.0, k: int = 100) -> float:
    """Shrink an observed rate/ratio toward `baseline` based on sample size `n`.

    With n=0 this returns exactly `baseline`. As n grows relative to `k`,
    the result moves toward `observed`.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    return (n / (n + k)) * observed + (k / (n + k)) * baseline


def sample_reliability(n: int, full_score_at: int = 200) -> float:
    return clamp(math.sqrt(max(n, 0) / full_score_at))


def score_from_edge(value: float | None, k: float, center: float = 0.5) -> float:
    """Map an edge-like value (e.g. ROI, CLV) onto a 0..1 score.

    `value=0` maps to `center` (neutral). Positive edges push the score up
    toward 1, negative edges push it down toward 0. `k` controls how quickly
    the score saturates - it should be picked based on the typical magnitude
    of the value being scored (ROI vs CLV are on different scales).
    """
    if value is None:
        return center
    return clamp(center + value * k)


def classify_wallet(final_score: float, resolved_trade_count: int, min_resolved: int = 20) -> str:
    if resolved_trade_count < min_resolved:
        return "insufficient_sample"
    if final_score >= 80:
        return "candidate_smart_wallet"
    if final_score >= 65:
        return "watchlist"
    return "ignore"


# ---------------------------------------------------------------------------
# Score component: one row of the transparent breakdown
# ---------------------------------------------------------------------------


@dataclass
class ScoreComponent:
    name: str
    weight: float
    raw_score: float  # 0..1
    note: str

    @property
    def contribution(self) -> float:
        return self.weight * self.raw_score


@dataclass
class Penalty:
    name: str
    points: float
    note: str


# ---------------------------------------------------------------------------
# Drawdown (reconstructed from realized PnL sequence ordered by close time)
# ---------------------------------------------------------------------------


def _parse_ts_loose(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 10**12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            except (TypeError, ValueError):
                return None
    return None


MIN_TRADES_FOR_DRAWDOWN = 5


def compute_drawdown_score(closed_positions: list[dict]) -> ScoreComponent:
    """Reconstruct a realized-PnL equity curve and score based on relative
    max drawdown. Requires closed_ts on each row to establish ordering.
    """
    dated = []
    for row in closed_positions:
        ts = _parse_ts_loose(row.get("closed_ts"))
        pnl = row.get("realized_pnl")
        if ts is not None and pnl is not None:
            dated.append((ts, float(pnl)))

    if len(dated) < MIN_TRADES_FOR_DRAWDOWN:
        return ScoreComponent(
            "drawdown_control",
            weight=10,
            raw_score=0.5,
            note=(
                f"only {len(dated)} resolved positions have a usable closed_ts "
                f"(need >= {MIN_TRADES_FOR_DRAWDOWN}) - drawdown left neutral"
            ),
        )

    dated.sort(key=lambda x: x[0])
    running = 0.0
    peak = 0.0
    max_dd = 0.0
    for _, pnl in dated:
        running += pnl
        peak = max(peak, running)
        max_dd = max(max_dd, peak - running)

    if peak <= 0:
        # Wallet never had positive cumulative realized PnL to draw down from.
        return ScoreComponent(
            "drawdown_control",
            weight=10,
            raw_score=0.5,
            note="cumulative realized PnL never went positive - drawdown ratio undefined, left neutral",
        )

    dd_ratio = max_dd / peak
    score = clamp(1 - dd_ratio)
    return ScoreComponent(
        "drawdown_control",
        weight=10,
        raw_score=score,
        note=f"max drawdown was {dd_ratio:.1%} of peak cumulative realized PnL across {len(dated)} resolved positions",
    )


# ---------------------------------------------------------------------------
# Niche specialization (per-category realized ROI, Bayesian-shrunk)
# ---------------------------------------------------------------------------

MIN_TRADES_PER_CATEGORY = 5
MIN_CATEGORIES_FOR_NICHE = 1


def compute_niche_score(closed_positions_with_category: list[dict]) -> ScoreComponent:
    by_category: dict[str, list[dict]] = {}
    for row in closed_positions_with_category:
        cat = row.get("category") or "uncategorized"
        by_category.setdefault(cat, []).append(row)

    qualifying = {cat: rows for cat, rows in by_category.items() if len(rows) >= MIN_TRADES_PER_CATEGORY}

    if not qualifying:
        return ScoreComponent(
            "niche_specialization",
            weight=15,
            raw_score=0.5,
            note=(
                f"no category has >= {MIN_TRADES_PER_CATEGORY} resolved trades "
                "(or category data missing from markets table) - left neutral"
            ),
        )

    best_cat = None
    best_shrunk_roi = None
    for cat, rows in qualifying.items():
        usable = [r for r in rows if r.get("realized_pnl") is not None]
        cost_basis = sum(
            abs(float(r["size"]) * float(r["avg_price"]))
            for r in usable
            if r.get("size") is not None and r.get("avg_price") is not None
        )
        if cost_basis <= 0:
            continue
        total_pnl = sum(float(r["realized_pnl"]) for r in usable)
        roi = total_pnl / cost_basis
        shrunk = bayesian_shrink(roi, n=len(usable), baseline=0.0, k=50)
        if best_shrunk_roi is None or shrunk > best_shrunk_roi:
            best_shrunk_roi = shrunk
            best_cat = cat

    if best_cat is None:
        return ScoreComponent(
            "niche_specialization",
            weight=15,
            raw_score=0.5,
            note="categories had enough trades but no usable cost-basis data - left neutral",
        )

    score = score_from_edge(best_shrunk_roi, k=5.0)
    return ScoreComponent(
        "niche_specialization",
        weight=15,
        raw_score=score,
        note=f"best category is '{best_cat}' with Bayesian-shrunk realized ROI {best_shrunk_roi:.3f} "
        f"({len(qualifying[best_cat])} resolved trades)",
    )


# ---------------------------------------------------------------------------
# Recency (exponentially time-weighted realized ROI)
# ---------------------------------------------------------------------------

RECENCY_HALF_LIFE_DAYS = 45
MIN_TRADES_FOR_RECENCY = 5


def compute_recency_score(closed_positions: list[dict], as_of: datetime | None = None) -> ScoreComponent:
    as_of = as_of or datetime.now(timezone.utc)
    dated = []
    for row in closed_positions:
        ts = _parse_ts_loose(row.get("closed_ts"))
        pnl = row.get("realized_pnl")
        size = row.get("size")
        avg_price = row.get("avg_price")
        if ts is not None and pnl is not None and size is not None and avg_price is not None:
            dated.append((ts, float(pnl), abs(float(size) * float(avg_price))))

    if len(dated) < MIN_TRADES_FOR_RECENCY:
        return ScoreComponent(
            "recency",
            weight=5,
            raw_score=0.5,
            note=f"only {len(dated)} resolved positions have full data for recency weighting - left neutral",
        )

    weighted_pnl = 0.0
    weighted_cost = 0.0
    for ts, pnl, cost in dated:
        age_days = max((as_of - ts).total_seconds() / 86400.0, 0.0)
        weight = 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)
        weighted_pnl += weight * pnl
        weighted_cost += weight * cost

    if weighted_cost <= 0:
        return ScoreComponent(
            "recency",
            weight=5,
            raw_score=0.5,
            note="recency-weighted cost basis was zero - left neutral",
        )

    recency_roi = weighted_pnl / weighted_cost
    score = score_from_edge(recency_roi, k=5.0)
    return ScoreComponent(
        "recency",
        weight=5,
        raw_score=score,
        note=f"recency-weighted realized ROI {recency_roi:.3f} (half-life {RECENCY_HALF_LIFE_DAYS}d, {len(dated)} trades)",
    )


# ---------------------------------------------------------------------------
# Liquidity-adjusted PnL (best-effort join to orderbook depth; honest neutral
# fallback since historical depth-at-trade-time is frequently unavailable)
# ---------------------------------------------------------------------------

THIN_BOOK_DEPTH_USD = 200.0


def compute_liquidity_adjusted_score(
    closed_positions: list[dict], depth_by_token: dict[str, float]
) -> ScoreComponent:
    """Discount realized PnL that came almost entirely from thin-book tokens.

    `depth_by_token` maps token_id -> average observed depth_3c (USD) from
    orderbook_snapshots. This is only ever a proxy for depth *at trade time*
    (snapshots are taken on whatever cadence `snapshot-books` was run at),
    so this component stays conservative and defaults to neutral whenever we
    don't have any matching depth data at all.
    """
    usable = [r for r in closed_positions if r.get("realized_pnl") is not None]
    if not usable:
        return ScoreComponent(
            "liquidity_adjusted_pnl",
            weight=10,
            raw_score=0.5,
            note="no resolved positions with realized_pnl - left neutral",
        )

    matched = [(r, depth_by_token.get(r.get("token_id"))) for r in usable]
    with_depth = [(r, d) for r, d in matched if d is not None]

    if not with_depth:
        return ScoreComponent(
            "liquidity_adjusted_pnl",
            weight=10,
            raw_score=0.5,
            note=(
                "no orderbook depth snapshots available for this wallet's tokens "
                "(run snapshot-books while these markets are active to populate this) - left neutral"
            ),
        )

    total_pnl = sum(float(r["realized_pnl"]) for r, _ in with_depth)
    thin_pnl = sum(float(r["realized_pnl"]) for r, d in with_depth if d < THIN_BOOK_DEPTH_USD)

    if total_pnl <= 0:
        # Can't meaningfully talk about "profit concentrated in illiquid
        # markets" if there's no net profit in the matched sample.
        return ScoreComponent(
            "liquidity_adjusted_pnl",
            weight=10,
            raw_score=0.5,
            note=f"depth data found for {len(with_depth)}/{len(usable)} positions but net realized PnL in that sample is not positive - left neutral",
        )

    thin_fraction = clamp(thin_pnl / total_pnl) if total_pnl > 0 else 0.0
    score = clamp(1 - thin_fraction)
    return ScoreComponent(
        "liquidity_adjusted_pnl",
        weight=10,
        raw_score=score,
        note=(
            f"{thin_fraction:.0%} of matched realized profit came from markets with "
            f"< ${THIN_BOOK_DEPTH_USD:.0f} visible depth (depth data available for "
            f"{len(with_depth)}/{len(usable)} positions)"
        ),
    )


# ---------------------------------------------------------------------------
# Exit quality - honestly left as a documented TODO
# ---------------------------------------------------------------------------


def compute_exit_quality_score() -> ScoreComponent:
    """Exit quality (did the wallet capture value well on manual exits, as
    opposed to holding to resolution) needs FIFO-matched entry/exit trade
    pairs per position, which this build doesn't reconstruct yet.

    Rather than approximate it with something that overlaps with
    Bayesian_ROI_score or CLV (and double-counts those components), this is
    left explicitly neutral until entry/exit matching is implemented.

    TODO: build a FIFO position ledger from wallet_trades (BUY opens, SELL
    reduces/closes) and compare each SELL's price against the token's
    subsequent price path, the same way scoring/clv.py does for BUYs.
    """
    return ScoreComponent(
        "exit_quality",
        weight=5,
        raw_score=0.5,
        note="not implemented - requires FIFO entry/exit trade matching not yet built; left neutral (see TODO in scoring/wallets.py)",
    )


# ---------------------------------------------------------------------------
# Penalties
# ---------------------------------------------------------------------------

ONE_HIT_WONDER_THRESHOLD = 0.60
CONCENTRATION_THRESHOLD = 0.50


def compute_penalties(
    resolved_trade_count: int,
    closed_positions: list[dict],
    avg_clv_24h: float | None,
) -> list[Penalty]:
    penalties: list[Penalty] = []

    if resolved_trade_count < 20:
        penalties.append(
            Penalty("low_sample_size", 15.0, f"only {resolved_trade_count} resolved trades (< 20)")
        )
    elif resolved_trade_count < 50:
        penalties.append(
            Penalty("low_sample_size", 5.0, f"only {resolved_trade_count} resolved trades (< 50 preferred)")
        )

    usable = [r for r in closed_positions if r.get("realized_pnl") is not None]
    total_pnl = sum(float(r["realized_pnl"]) for r in usable)
    if len(usable) > 1 and total_pnl > 0:
        max_single = max(float(r["realized_pnl"]) for r in usable)
        if max_single / total_pnl > ONE_HIT_WONDER_THRESHOLD:
            penalties.append(
                Penalty(
                    "one_hit_wonder",
                    15.0,
                    f"a single resolved position accounts for {max_single / total_pnl:.0%} of total realized PnL",
                )
            )

    if avg_clv_24h is not None and avg_clv_24h < 0:
        penalties.append(
            Penalty("negative_clv", 15.0, f"average 24h CLV is negative ({avg_clv_24h:.4f})")
        )

    if usable:
        by_market: dict[str, float] = {}
        for r in usable:
            by_market[r.get("market_id", "")] = by_market.get(r.get("market_id", ""), 0.0) + abs(
                float(r["realized_pnl"])
            )
        total_abs_pnl = sum(by_market.values())
        if total_abs_pnl > 0:
            max_market_share = max(by_market.values()) / total_abs_pnl
            if max_market_share > CONCENTRATION_THRESHOLD:
                penalties.append(
                    Penalty(
                        "concentration_risk",
                        10.0,
                        f"a single market accounts for {max_market_share:.0%} of total absolute realized PnL",
                    )
                )

    return penalties


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _fetch_closed_positions_with_category(wallet: str, engine: Engine) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT c.market_id, c.token_id, c.size, c.avg_price, c.realized_pnl, c.closed_ts,
                       m.category
                FROM wallet_closed_positions c
                LEFT JOIN markets m ON m.market_id = c.market_id
                WHERE lower(c.wallet) = lower(:wallet)
            """),
            {"wallet": wallet},
        ).mappings().all()
    return [dict(r) for r in rows]


def _fetch_depth_by_token(wallet: str, engine: Engine) -> dict[str, float]:
    """Average observed depth_3c per token this wallet has traded, from
    whatever orderbook snapshots happen to exist. This is a coarse proxy,
    not a depth-at-trade-time lookup - see compute_liquidity_adjusted_score.
    """
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT b.token_id, AVG(b.depth_3c) AS avg_depth
                FROM orderbook_snapshots b
                WHERE b.token_id IN (
                    SELECT DISTINCT token_id FROM wallet_trades WHERE lower(wallet) = lower(:wallet)
                )
                GROUP BY b.token_id
            """),
            {"wallet": wallet},
        ).mappings().all()
    return {r["token_id"]: float(r["avg_depth"]) for r in rows if r["avg_depth"] is not None}


def compute_wallet_score(wallet: str, engine: Engine | None = None) -> WalletScore:
    engine = engine or get_engine()

    resolved_stats = compute_resolved_pnl_stats(wallet, engine=engine)
    unrealized_stats = compute_unrealized_pnl_stats(wallet, engine=engine)
    clv_summary = summarize_wallet_clv(wallet, engine=engine)
    closed_positions = _fetch_closed_positions_with_category(wallet, engine)
    depth_by_token = _fetch_depth_by_token(wallet, engine)

    n_resolved = resolved_stats.resolved_trade_count

    # --- Bayesian ROI (realized only) ---
    shrunk_roi = None
    if resolved_stats.realized_roi is not None:
        shrunk_roi = bayesian_shrink(resolved_stats.realized_roi, n=n_resolved, baseline=0.0, k=100)
    roi_component = ScoreComponent(
        "bayesian_roi",
        weight=20,
        raw_score=score_from_edge(shrunk_roi, k=5.0),
        note=(
            f"realized ROI {resolved_stats.realized_roi:.3f} shrunk to {shrunk_roi:.3f} over {n_resolved} resolved trades"
            if shrunk_roi is not None
            else f"realized ROI unavailable ({resolved_stats.data_note}) - left neutral"
        ),
    )

    # --- CLV ---
    clv_value = clv_summary.avg_clv_24h if clv_summary.avg_clv_24h is not None else clv_summary.avg_clv_close
    clv_component = ScoreComponent(
        "closing_line_value",
        weight=15,
        raw_score=score_from_edge(clv_value, k=10.0),
        note=clv_summary.data_note,
    )

    # --- Sample size ---
    reliability = sample_reliability(n_resolved, full_score_at=50)
    sample_component = ScoreComponent(
        "sample_size",
        weight=10,
        raw_score=reliability,
        note=f"{n_resolved} resolved trades (full credit at 50+)",
    )

    drawdown_component = compute_drawdown_score(closed_positions)
    niche_component = compute_niche_score(closed_positions)
    recency_component = compute_recency_score(closed_positions)
    liquidity_component = compute_liquidity_adjusted_score(closed_positions, depth_by_token)
    exit_component = compute_exit_quality_score()

    # --- Timing edge: how much of the eventual move already happened early ---
    timing_component = ScoreComponent(
        "timing_edge",
        weight=10,
        raw_score=score_from_edge(clv_summary.avg_clv_1h, k=10.0),
        note=(
            f"average 1h CLV {clv_summary.avg_clv_1h:.4f} over {clv_summary.sample_size_1h} eligible trades"
            if clv_summary.avg_clv_1h is not None
            else "no 1h CLV data available - left neutral"
        ),
    )

    components = [
        roi_component,
        clv_component,
        niche_component,
        sample_component,
        drawdown_component,
        liquidity_component,
        timing_component,
        exit_component,
        recency_component,
    ]

    weighted_sum = sum(c.contribution for c in components)  # 0..100 (weights sum to 100)

    penalties = compute_penalties(n_resolved, closed_positions, clv_summary.avg_clv_24h)
    total_penalty = sum(p.points for p in penalties)

    final_score = clamp(weighted_sum - total_penalty, 0.0, 100.0)
    classification = classify_wallet(final_score, n_resolved)

    notes = (
        f"Resolved: {resolved_stats.data_note}. Unrealized PnL (NOT used in score): "
        f"${unrealized_stats.total_unrealized_pnl:.2f} across {unrealized_stats.open_position_count} open positions. "
        f"CLV: {clv_summary.data_note}."
    )

    component_breakdown = {
        "components": [
            {
                "name": c.name,
                "weight": c.weight,
                "raw_score": round(c.raw_score, 4),
                "contribution": round(c.contribution, 3),
                "note": c.note,
            }
            for c in components
        ],
        "penalties": [{"name": p.name, "points": p.points, "note": p.note} for p in penalties],
        "weighted_sum_before_penalty": round(weighted_sum, 3),
        "total_penalty": round(total_penalty, 3),
    }

    return WalletScore(
        wallet=wallet.lower(),
        total_trades=n_resolved,  # kept as "total_trades" for dataclass compat; this is RESOLVED trades
        sample_reliability=reliability,
        roi_estimate=resolved_stats.realized_roi if resolved_stats.realized_roi is not None else 0.0,
        shrunk_roi=shrunk_roi if shrunk_roi is not None else 0.0,
        clv_score=clv_component.raw_score,
        drawdown_score=drawdown_component.raw_score,
        timing_score=timing_component.raw_score,
        niche_score=niche_component.raw_score,
        penalty=total_penalty,
        final_score=final_score,
        classification=classification,
        # Extra fields not on the original dataclass - see models.py update.
        realized_pnl=resolved_stats.total_realized_pnl,
        realized_roi=resolved_stats.realized_roi,
        resolved_trade_count=n_resolved,
        unrealized_pnl=unrealized_stats.total_unrealized_pnl,
        open_position_count=unrealized_stats.open_position_count,
        liquidity_score=liquidity_component.raw_score,
        recency_score=recency_component.raw_score,
        exit_quality_score=exit_component.raw_score,
        clv_sample_size=clv_summary.sample_size_24h,
        notes=notes,
        component_json=json.dumps(component_breakdown),
    )


def score_all_wallets(engine: Engine | None = None) -> list[WalletScore]:
    engine = engine or get_engine()
    with engine.begin() as conn:
        wallets = [
            row["wallet"]
            for row in conn.execute(text("SELECT DISTINCT wallet FROM wallet_trades")).mappings().all()
        ]

    scores = [compute_wallet_score(w, engine=engine) for w in wallets]

    with engine.begin() as conn:
        for s in scores:
            conn.execute(
                text("""
                    INSERT OR REPLACE INTO wallet_scores (
                        wallet, total_trades, sample_reliability, roi_estimate,
                        shrunk_roi, clv_score, drawdown_score, timing_score,
                        niche_score, penalty, final_score, classification, notes,
                        realized_pnl, realized_roi, resolved_trade_count,
                        unrealized_pnl, open_position_count,
                        liquidity_score, recency_score, exit_quality_score,
                        clv_sample_size, component_json,
                        updated_at
                    )
                    VALUES (
                        :wallet, :total_trades, :sample_reliability, :roi_estimate,
                        :shrunk_roi, :clv_score, :drawdown_score, :timing_score,
                        :niche_score, :penalty, :final_score, :classification, :notes,
                        :realized_pnl, :realized_roi, :resolved_trade_count,
                        :unrealized_pnl, :open_position_count,
                        :liquidity_score, :recency_score, :exit_quality_score,
                        :clv_sample_size, :component_json,
                        CURRENT_TIMESTAMP
                    )
                """),
                {
                    "wallet": s.wallet,
                    "total_trades": s.total_trades,
                    "sample_reliability": s.sample_reliability,
                    "roi_estimate": s.roi_estimate,
                    "shrunk_roi": s.shrunk_roi,
                    "clv_score": s.clv_score,
                    "drawdown_score": s.drawdown_score,
                    "timing_score": s.timing_score,
                    "niche_score": s.niche_score,
                    "penalty": s.penalty,
                    "final_score": s.final_score,
                    "classification": s.classification,
                    "notes": s.notes,
                    "realized_pnl": s.realized_pnl,
                    "realized_roi": s.realized_roi,
                    "resolved_trade_count": s.resolved_trade_count,
                    "unrealized_pnl": s.unrealized_pnl,
                    "open_position_count": s.open_position_count,
                    "liquidity_score": s.liquidity_score,
                    "recency_score": s.recency_score,
                    "exit_quality_score": s.exit_quality_score,
                    "clv_sample_size": s.clv_sample_size,
                    "component_json": s.component_json,
                },
            )

    return scores
