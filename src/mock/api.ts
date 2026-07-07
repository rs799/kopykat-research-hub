// KopyKat mock API layer.
// All functions return the same shapes a real backend at http://localhost:8000 would return.
// Swap the implementations with fetch() calls when the backend is ready — the UI does not care.

import {
  alerts,
  backtests,
  dataHealth,
  niches,
  overview,
  paperSim,
  rankingsForNiche,
  wallets,
  type ConsensusAlert,
  type NicheKey,
  type Wallet,
} from "./data";

const delay = <T,>(v: T, ms = 120): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

export const api = {
  // GET /api/overview
  overview: () => delay(overview),
  // GET /api/niches
  niches: () => delay(niches),
  // GET /api/niches/{niche}/wallet-discovery
  walletDiscovery: (niche: NicheKey) => delay(wallets.filter((w) => w.niche === niche)),
  // GET /api/niches/{niche}/wallet-rankings
  walletRankings: (niche: NicheKey) => delay(rankingsForNiche(niche)),
  // GET /api/consensus-alerts
  alerts: () => delay(alerts),
  // GET /api/alerts/{id}
  alert: (id: string): Promise<ConsensusAlert | undefined> => delay(alerts.find((a) => a.id === id)),
  // GET /api/wallets
  wallets: () => delay(wallets),
  // POST /api/wallets
  addWallet: (address: string, niche: NicheKey): Promise<Wallet> => {
    const w: Wallet = {
      address,
      niche,
      marketsObserved: 0,
      resolvedObservations: 0,
      realizedPnl: 0,
      roi: 0,
      clv: 0,
      sampleSize: 0,
      status: "watch",
      reason: "Manually added, awaiting observations",
      firstSeen: new Date().toISOString().slice(0, 10),
      lastSeen: new Date().toISOString().slice(0, 10),
      tags: ["manual"],
      source: "manual-seed",
      nichesObserved: [niche],
    };
    wallets.unshift(w);
    return delay(w);
  },
  // DELETE /api/wallets/{wallet}
  removeWallet: (address: string) => {
    const idx = wallets.findIndex((w) => w.address === address);
    if (idx >= 0) wallets.splice(idx, 1);
    return delay({ ok: true });
  },
  // GET /api/data-health
  dataHealth: () => delay(dataHealth),
  // GET /api/paper-simulation
  paperSimulation: () => delay(paperSim),
  // GET /api/backtests
  backtests: () => delay(backtests),
  // GET /api/trade-feed  (REAL backend call — not mock)
  tradeFeed: async (
    niche?: string,
    side?: "BUY" | "SELL",
    limit: number = 100,
  ): Promise<TradeFeedItem[]> => {
    const params = new URLSearchParams();
    if (niche && niche !== "all") params.set("niche", niche);
    if (side) params.set("side", side);
    if (limit) params.set("limit", String(limit));
    const url = `http://localhost:8000/api/trade-feed${params.toString() ? `?${params}` : ""}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`trade-feed ${res.status}`);
    return (await res.json()) as TradeFeedItem[];
  },
};

export interface TradeFeedItem {
  walletAddress: string;
  niche: string | null;
  walletScore: number | null;
  walletClassification: string | null;
  side: string | null;
  marketId: string | null;
  conditionId: string | null;
  tokenId: string | null;
  outcome: string | null;
  price: number | null;
  size: number | null;
  usdcSize: number | null;
  timestamp: string | null;
}

export type Api = typeof api;
