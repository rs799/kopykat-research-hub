// KopyKat mock data — FRONTEND ONLY. No real network, no real wallets.
// All numbers, wallets, markets, and PnL are fabricated for UI prototyping.
// Keep this file the single source of truth so it can later be swapped for a real API.

export type NicheKey = "crypto" | "sports" | "macro" | "tech" | "global";

export interface Niche {
  key: NicheKey;
  name: string;
  markets: number;
  discoveredWallets: number;
  qualifiedWallets: number;
  avgLiquidity: number;
  alerts: number;
  warnings: number;
  status: "healthy" | "degraded" | "stale";
  description: string;
}

export interface Wallet {
  address: string;
  niche: NicheKey;
  marketsObserved: number;
  resolvedObservations: number;
  realizedPnl: number;
  roi: number;
  clv: number;
  sampleSize: number;
  status: "qualified" | "watch" | "rejected" | "suspicious";
  reason: string;
  firstSeen: string;
  lastSeen: string;
  tags: string[];
  source: string;
  nichesObserved: NicheKey[];
}

export interface RankedWallet extends Wallet {
  rank: number;
  nicheScore: number;
  globalScore: number;
  clvScore: number;
  drawdown: number;
  specialty: string;
  recency: number;
  flags: string[];
  breakdown: {
    bayesianRoi: number;
    clv: number;
    sampleSize: number;
    drawdownControl: number;
    liquidityAdj: number;
    timingEdge: number;
    recency: number;
    penalties: number;
  };
}

export interface ConsensusAlert {
  id: string;
  strength: number; // 0-100
  niche: NicheKey;
  market: string;
  side: string;
  walletsAligned: number;
  avgWalletScore: number;
  firstPrice: number;
  currentPrice: number;
  priceMoved: number;
  spread: number;
  liquidity: number;
  disagreement: number;
  status: "watch" | "paper" | "rejected";
  reason: string;
  observedAt: string;
  consensusScore: number;
  avgWalletQuality: number;
  suggestedMaxPrice: number;
  wallets: {
    address: string;
    score: number;
    nicheScore: number;
    observedAt: string;
    observedPrice: number;
    size: number;
    clvHistory: number;
    status: string;
  }[];
  disagreementDetail: {
    address: string;
    side: string;
    size: number;
    note: string;
  }[];
}

export interface PaperOrder {
  id: string;
  time: string;
  market: string;
  side: string;
  price: number;
  size: number;
  status: "filled" | "partial" | "missed";
  linkedAlert: string;
}

export interface PaperPosition {
  market: string;
  side: string;
  avgPrice: number;
  size: number;
  markPrice: number;
  unrealized: number;
}

export interface Backtest {
  id: string;
  niche: NicheKey;
  strategy: string;
  roi: number;
  maxDrawdown: number;
  fillRate: number;
  missedFillRate: number;
  avgAlertStrength: number;
  runs: number;
}

export interface Warning {
  timestamp: string;
  endpoint: string;
  wallet: string;
  severity: "low" | "med" | "high";
  warning: string;
  rawField: string;
  parsedField: string;
  message: string;
}

// ---------- helpers ----------
const rand = (seed: number) => {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296;
    return s / 4294967296;
  };
};

const hex = (r: () => number, len = 40) =>
  "0x" + Array.from({ length: len }, () => "0123456789abcdef"[Math.floor(r() * 16)]).join("");

const pick = <T,>(arr: T[], r: () => number) => arr[Math.floor(r() * arr.length)];

// ---------- niches ----------
export const niches: Niche[] = [
  {
    key: "crypto",
    name: "Crypto",
    markets: 42,
    discoveredWallets: 318,
    qualifiedWallets: 47,
    avgLiquidity: 128_400,
    alerts: 6,
    warnings: 2,
    status: "healthy",
    description: "BTC / ETH price levels, ETF flows, protocol events.",
  },
  {
    key: "sports",
    name: "Sports",
    markets: 63,
    discoveredWallets: 421,
    qualifiedWallets: 39,
    avgLiquidity: 84_200,
    alerts: 4,
    warnings: 0,
    status: "healthy",
    description: "Match winners, tournament outcomes, prop-style markets.",
  },
  {
    key: "macro",
    name: "Macro",
    markets: 18,
    discoveredWallets: 112,
    qualifiedWallets: 21,
    avgLiquidity: 210_500,
    alerts: 2,
    warnings: 1,
    status: "degraded",
    description: "Central bank rate decisions, CPI prints, GDP surprises.",
  },
  {
    key: "tech",
    name: "Tech & Culture",
    markets: 27,
    discoveredWallets: 189,
    qualifiedWallets: 22,
    avgLiquidity: 46_900,
    alerts: 3,
    warnings: 4,
    status: "degraded",
    description: "Product launches, keynote outcomes, box-office milestones.",
  },
  {
    key: "global",
    name: "Global Events",
    markets: 31,
    discoveredWallets: 244,
    qualifiedWallets: 28,
    avgLiquidity: 96_300,
    alerts: 5,
    warnings: 1,
    status: "healthy",
    description: "Elections, treaties, geopolitical binary events.",
  },
];

// ---------- wallets ----------
const wr = rand(42);
const statuses: Wallet["status"][] = ["qualified", "qualified", "qualified", "watch", "rejected", "suspicious"];
const reasons: Record<Wallet["status"], string[]> = {
  qualified: ["Consistent CLV", "Deep sample, low drawdown", "Sharp in-niche edge"],
  watch: ["Small sample", "Recent regime shift", "Volatile ROI"],
  rejected: ["Sample too small", "Negative CLV", "Suspected copy-trader"],
  suspicious: ["Bot-like timing", "Sybil cluster candidate", "Wash-trade pattern"],
};
const tagsPool = ["sharp", "whale", "retail", "regional", "event-only", "late-fader", "opener", "closer"];
const sources = ["subgraph-crawl", "activity-feed", "leaderboard", "referrer-graph", "manual-seed"];

export const wallets: Wallet[] = Array.from({ length: 64 }, (_, i) => {
  const niche = pick(niches, wr).key;
  const sample = 8 + Math.floor(wr() * 220);
  const roi = +(wr() * 0.9 - 0.2).toFixed(3);
  const pnl = Math.round(roi * (5_000 + wr() * 40_000));
  const status = statuses[Math.floor(wr() * statuses.length)];
  const nichesObserved = Array.from(new Set([niche, pick(niches, wr).key])) as NicheKey[];
  return {
    address: hex(wr),
    niche,
    marketsObserved: 4 + Math.floor(wr() * 60),
    resolvedObservations: sample,
    realizedPnl: pnl,
    roi,
    clv: +(wr() * 0.14 - 0.03).toFixed(3),
    sampleSize: sample,
    status,
    reason: pick(reasons[status], wr),
    firstSeen: `2025-${String(1 + Math.floor(wr() * 6)).padStart(2, "0")}-${String(1 + Math.floor(wr() * 27)).padStart(2, "0")}`,
    lastSeen: `2026-0${1 + Math.floor(wr() * 6)}-${String(1 + Math.floor(wr() * 27)).padStart(2, "0")}`,
    tags: Array.from(new Set([pick(tagsPool, wr), pick(tagsPool, wr)])),
    source: pick(sources, wr),
    nichesObserved,
    _i: i,
  } as Wallet;
});

// ---------- rankings ----------
export function rankingsForNiche(niche: NicheKey): RankedWallet[] {
  const rr = rand(niche.length * 97 + 7);
  const list = wallets
    .filter((w) => w.niche === niche && w.status !== "rejected")
    .slice(0, 12)
    .map((w, idx) => {
      const nicheScore = +(60 + rr() * 38).toFixed(1);
      const globalScore = +(nicheScore - rr() * 12).toFixed(1);
      const b = {
        bayesianRoi: +(rr() * 30 + 40).toFixed(1),
        clv: +(rr() * 25 + 55).toFixed(1),
        sampleSize: +(rr() * 30 + 40).toFixed(1),
        drawdownControl: +(rr() * 30 + 50).toFixed(1),
        liquidityAdj: +(rr() * 20 + 60).toFixed(1),
        timingEdge: +(rr() * 30 + 45).toFixed(1),
        recency: +(rr() * 20 + 70).toFixed(1),
        penalties: -+(rr() * 15).toFixed(1),
      };
      return {
        ...w,
        rank: idx + 1,
        nicheScore,
        globalScore,
        clvScore: +(rr() * 30 + 55).toFixed(1),
        drawdown: +(rr() * 0.25 + 0.05).toFixed(3),
        specialty: pick(["opener", "closer", "event-only", "high-liquidity"], rr),
        recency: Math.floor(rr() * 14) + 1,
        flags: rr() > 0.7 ? [pick(["small-sample", "regime-shift", "clustered"], rr)] : [],
        breakdown: b,
      } as RankedWallet;
    })
    .sort((a, b) => b.nicheScore - a.nicheScore)
    .map((w, i) => ({ ...w, rank: i + 1 }));
  return list;
}

// ---------- alerts ----------
const marketExamples: Record<NicheKey, string[]> = {
  crypto: [
    "BTC above $120K by Jan 31?",
    "ETH above $6K by Feb 15?",
    "Spot Solana ETF approved in Q1?",
    "Any L2 to flip Base TVL in 30d?",
  ],
  sports: [
    "Real Madrid to win UCL 2026?",
    "Chiefs to reach Super Bowl LX?",
    "Djokovic wins Australian Open?",
    "Man City top of PL on March 1?",
  ],
  macro: [
    "Fed cuts 25bps at March meeting?",
    "US CPI YoY above 3.2% next print?",
    "ECB holds rates in February?",
    "Q4 US GDP above 2.5% (advance)?",
  ],
  tech: [
    "Apple to announce foldable in H1?",
    "GPT-6 released by April 15?",
    "Tesla Robotaxi public launch in Q1?",
    "Nvidia keynote reveals new B-series?",
  ],
  global: [
    "Ceasefire signed in Region X by March?",
    "UK snap election called before June?",
    "SpaceX crewed Starship flight this year?",
    "COP outcome: binding emissions target?",
  ],
};

const ar = rand(9001);
export const alerts: ConsensusAlert[] = Array.from({ length: 14 }, (_, i) => {
  const niche = pick(niches, ar).key;
  const firstPrice = +(0.2 + ar() * 0.5).toFixed(2);
  const currentPrice = +Math.min(0.98, Math.max(0.02, firstPrice + (ar() - 0.4) * 0.18)).toFixed(2);
  const walletsAligned = 3 + Math.floor(ar() * 8);
  const strength = Math.min(99, Math.round(45 + ar() * 55));
  const status: ConsensusAlert["status"] = strength > 78 ? "paper" : strength > 55 ? "watch" : "rejected";
  const reasonMap: Record<ConsensusAlert["status"], string> = {
    watch: "Strength above watchlist threshold but liquidity thin.",
    paper: "Meets consensus + quality thresholds. Routed to paper sim.",
    rejected: "Disagreement count high or wallet quality below floor.",
  };
  return {
    id: `AL-${String(1000 + i)}`,
    strength,
    niche,
    market: pick(marketExamples[niche], ar),
    side: ar() > 0.5 ? "YES" : "NO",
    walletsAligned,
    avgWalletScore: +(70 + ar() * 25).toFixed(1),
    firstPrice,
    currentPrice,
    priceMoved: +(currentPrice - firstPrice).toFixed(2),
    spread: +(0.01 + ar() * 0.04).toFixed(3),
    liquidity: Math.round(20_000 + ar() * 250_000),
    disagreement: Math.floor(ar() * 4),
    status,
    reason: reasonMap[status],
    observedAt: `2026-07-0${1 + (i % 5)} ${String(9 + (i % 8)).padStart(2, "0")}:${String((i * 7) % 60).padStart(2, "0")}`,
    consensusScore: +(strength / 100).toFixed(2),
    avgWalletQuality: +(70 + ar() * 25).toFixed(1),
    suggestedMaxPrice: +(currentPrice + 0.03).toFixed(2),
    wallets: Array.from({ length: walletsAligned }, () => ({
      address: hex(ar),
      score: +(65 + ar() * 30).toFixed(1),
      nicheScore: +(65 + ar() * 30).toFixed(1),
      observedAt: `2026-07-0${1 + Math.floor(ar() * 4)} ${String(9 + Math.floor(ar() * 8)).padStart(2, "0")}:${String(Math.floor(ar() * 59)).padStart(2, "0")}`,
      observedPrice: +(firstPrice + (ar() - 0.5) * 0.04).toFixed(2),
      size: Math.round(500 + ar() * 8000),
      clvHistory: +(ar() * 0.1 - 0.02).toFixed(3),
      status: pick(["active", "trimmed", "closed"], ar),
    })),
    disagreementDetail: Array.from({ length: Math.floor(ar() * 3) }, () => ({
      address: hex(ar),
      side: ar() > 0.5 ? "YES" : "NO",
      size: Math.round(500 + ar() * 4000),
      note: pick(["Contrarian sharp", "Hedged position", "Different thesis"], ar),
    })),
  };
});

// ---------- paper simulation ----------
export const paperSim = {
  balance: 100_000,
  openPositions: 6,
  realizedPnl: 3_420,
  unrealizedPnl: 812,
  winRate: 0.58,
  maxDrawdown: -0.11,
  fillRate: 0.82,
  missedFillRate: 0.18,
  orders: Array.from({ length: 10 }, (_, i) => {
    const r = rand(500 + i);
    const st = pick(["filled", "filled", "partial", "missed"] as const, r);
    return {
      id: `PO-${2000 + i}`,
      time: `2026-07-0${1 + (i % 5)} 1${i % 9}:${String((i * 13) % 60).padStart(2, "0")}`,
      market: pick(marketExamples[pick(niches, r).key], r),
      side: r() > 0.5 ? "YES" : "NO",
      price: +(0.3 + r() * 0.4).toFixed(2),
      size: Math.round(500 + r() * 4000),
      status: st,
      linkedAlert: `AL-${1000 + (i % 14)}`,
    } as PaperOrder;
  }),
  positions: Array.from({ length: 6 }, (_, i) => {
    const r = rand(700 + i);
    const avg = +(0.3 + r() * 0.4).toFixed(2);
    const mark = +(avg + (r() - 0.4) * 0.1).toFixed(2);
    const size = Math.round(500 + r() * 4000);
    return {
      market: pick(marketExamples[pick(niches, r).key], r),
      side: r() > 0.5 ? "YES" : "NO",
      avgPrice: avg,
      size,
      markPrice: mark,
      unrealized: Math.round((mark - avg) * size),
    } as PaperPosition;
  }),
};

// ---------- backtests ----------
export const backtests: Backtest[] = niches.map((n, i) => {
  const r = rand(800 + i);
  return {
    id: `BT-${300 + i}`,
    niche: n.key,
    strategy: pick(["consensus>=3, score>=75", "consensus>=4, score>=80", "sharp-only, CLV>0.05"], r),
    roi: +(r() * 0.5 - 0.05).toFixed(3),
    maxDrawdown: -+(0.05 + r() * 0.2).toFixed(3),
    fillRate: +(0.65 + r() * 0.3).toFixed(2),
    missedFillRate: +(0.05 + r() * 0.25).toFixed(2),
    avgAlertStrength: +(60 + r() * 30).toFixed(1),
    runs: 20 + Math.floor(r() * 200),
  };
});

// Equity curve mock
export const equityCurve = Array.from({ length: 60 }, (_, i) => {
  const r = rand(9 + i);
  return { day: i + 1, equity: 100_000 + Math.round(Math.sin(i / 6) * 1500 + i * 120 + r() * 400) };
});

// ---------- data health ----------
export const dataHealth = {
  endpoints: [
    { name: "activity-feed (MOCK)", status: "ok", lastIngestion: "2s ago" },
    { name: "markets (MOCK)", status: "ok", lastIngestion: "4s ago" },
    { name: "wallets-index (MOCK)", status: "degraded", lastIngestion: "1m 20s ago" },
    { name: "resolutions (MOCK)", status: "ok", lastIngestion: "12s ago" },
  ],
  rawRows: 1_284_902,
  lifecycleEvents: 42_310,
  unresolvedIssues: 7,
  warnings: Array.from({ length: 9 }, (_, i) => {
    const r = rand(1200 + i);
    const sev = pick(["low", "med", "high"] as const, r);
    return {
      timestamp: `2026-07-0${1 + (i % 5)} ${String(10 + (i % 12)).padStart(2, "0")}:${String((i * 11) % 60).padStart(2, "0")}`,
      endpoint: pick(["activity-feed", "markets", "wallets-index", "resolutions"], r),
      wallet: hex(r),
      severity: sev,
      warning: pick(["schema drift", "missing field", "type mismatch", "duplicate row"], r),
      rawField: pick(["outcome_idx", "px", "size_raw", "resolved_at"], r),
      parsedField: pick(["outcome", "price", "size", "resolvedAt"], r),
      message: pick(
        [
          "Field renamed upstream; using fallback parser.",
          "Null value where numeric expected; row skipped.",
          "Duplicate event id; deduped by (id, ts).",
          "Type coerced from string to number.",
        ],
        r,
      ),
    } as Warning;
  }),
};

// ---------- overview ----------
export const overview = {
  activeNiches: niches.length,
  discoveredWallets: wallets.length,
  qualifiedWallets: wallets.filter((w) => w.status === "qualified").length,
  consensusAlerts: alerts.filter((a) => a.status !== "rejected").length,
  rejectedAlerts: alerts.filter((a) => a.status === "rejected").length,
  paperPnl: paperSim.realizedPnl + paperSim.unrealizedPnl,
  parserWarnings: dataHealth.warnings.length,
  backendStatus: "MOCK",
  mode: "PAPER ONLY",
};
