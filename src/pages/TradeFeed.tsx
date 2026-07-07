import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, type TradeFeedItem } from "@/mock/api";
import { Addr, ExplainCard, Pill, SectionHeader } from "@/components/kk/Primitives";
import { cn } from "@/lib/utils";

const NICHES = ["all", "crypto", "sports", "tech", "macro", "global"] as const;
const SIDES = ["all", "BUY", "SELL"] as const;
const LIMITS = [25, 50, 100, 200] as const;

function relTime(iso: string | null): string {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "—";
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function scoreTone(score: number | null): "success" | "warning" | "muted" {
  if (score == null) return "muted";
  if (score >= 75) return "success";
  if (score >= 50) return "warning";
  return "muted";
}

function nicheTone(n: string | null): "info" | "accent" | "success" | "warning" | "muted" {
  switch (n) {
    case "crypto": return "accent";
    case "sports": return "success";
    case "tech": return "info";
    case "macro": return "warning";
    case "global": return "muted";
    default: return "muted";
  }
}

export default function TradeFeed() {
  const navigate = useNavigate();
  const [niche, setNiche] = useState<(typeof NICHES)[number]>("all");
  const [side, setSide] = useState<(typeof SIDES)[number]>("all");
  const [limit, setLimit] = useState<number>(100);
  const [items, setItems] = useState<TradeFeedItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [, forceTick] = useState(0);
  const timerRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.tradeFeed(
        niche,
        side === "all" ? undefined : (side as "BUY" | "SELL"),
        limit,
      );
      setItems(Array.isArray(data) ? data : []);
      setLastRefresh(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load trade feed");
    } finally {
      setLoading(false);
    }
  }, [niche, side, limit]);

  useEffect(() => {
    load();
  }, [load]);

  // 15s auto-refresh
  useEffect(() => {
    if (timerRef.current) window.clearInterval(timerRef.current);
    timerRef.current = window.setInterval(load, 15000);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [load]);

  // tick every 30s so relative timestamps update
  useEffect(() => {
    const id = window.setInterval(() => forceTick((n) => n + 1), 30000);
    return () => window.clearInterval(id);
  }, []);

  const handleWalletClick = (address: string) => {
    try {
      navigator.clipboard.writeText(address);
      toast.success("Wallet address copied");
    } catch {
      /* ignore */
    }
    navigate(`/wallets?focus=${address}`);
  };

  const refreshLabel = useMemo(
    () => (lastRefresh ? lastRefresh.toLocaleTimeString(undefined, { hour12: false }) : "—"),
    [lastRefresh],
  );

  return (
    <div className="space-y-4">
      <ExplainCard title="What is the trade feed?">
        A chronological feed of real trades made by wallets KopyKat is tracking. Each trade is shown with that
        wallet&apos;s research score for context. This is observation only — nothing here places a trade or
        recommends one.
      </ExplainCard>

      <div className="panel p-3">
        <SectionHeader
          title="Trade feed"
          subtitle="Live tracked-wallet activity, newest first"
          right={
            <div className="mono flex items-center gap-3 text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
              <span>
                LAST REFRESH <span className="text-foreground">{refreshLabel}</span>
              </span>
              <span className={cn(loading ? "text-info" : "text-success")}>
                {loading ? "◌ SYNCING" : "● LIVE"}
              </span>
              <button
                onClick={load}
                className="border border-border px-2 py-0.5 hover:border-accent hover:text-accent"
              >
                REFRESH
              </button>
            </div>
          }
        />

        <div className="flex flex-wrap items-end gap-3 border-b border-border pb-2">
          <FilterGroup label="NICHE">
            {NICHES.map((n) => (
              <FilterBtn key={n} active={niche === n} onClick={() => setNiche(n)}>
                {n}
              </FilterBtn>
            ))}
          </FilterGroup>
          <FilterGroup label="SIDE">
            {SIDES.map((s) => (
              <FilterBtn key={s} active={side === s} onClick={() => setSide(s)}>
                {s}
              </FilterBtn>
            ))}
          </FilterGroup>
          <FilterGroup label="LIMIT">
            {LIMITS.map((l) => (
              <FilterBtn key={l} active={limit === l} onClick={() => setLimit(l)}>
                {l}
              </FilterBtn>
            ))}
          </FilterGroup>
        </div>

        {error && (
          <div className="mono mt-3 border border-destructive/50 bg-destructive/10 px-3 py-2 text-[11px] text-destructive">
            ERR // {error} — is the backend running at http://localhost:8000 ?
          </div>
        )}

        {!error && items.length === 0 && !loading && (
          <div className="mono mt-3 border border-border bg-muted/20 px-3 py-6 text-center text-[11px] text-muted-foreground">
            NO TRADES YET. RUN <span className="text-accent">discover-and-score-wallets</span> ON THE BACKEND TO
            POPULATE TRACKED WALLETS AND PULL THEIR TRADE HISTORY.
          </div>
        )}

        {items.length > 0 && (
          <div className="mt-2 overflow-x-auto">
            <table className="mono w-full min-w-[900px] border-collapse text-[11px]">
              <thead>
                <tr className="border-b border-border text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
                  <Th>Wallet</Th>
                  <Th>Niche</Th>
                  <Th className="text-right">Score</Th>
                  <Th>Class</Th>
                  <Th>Side</Th>
                  <Th>Market / Outcome</Th>
                  <Th className="text-right">Price</Th>
                  <Th className="text-right">Size (USDC)</Th>
                  <Th className="text-right">Time</Th>
                </tr>
              </thead>
              <tbody>
                {items.map((t, i) => {
                  const isBuy = t.side?.toUpperCase() === "BUY";
                  const isSell = t.side?.toUpperCase() === "SELL";
                  return (
                    <tr
                      key={`${t.walletAddress}-${t.timestamp}-${i}`}
                      className="border-b border-border/40 hover:bg-muted/20"
                    >
                      <Td>
                        <button
                          onClick={() => handleWalletClick(t.walletAddress)}
                          className="hover:text-accent hover:underline"
                          title={`${t.walletAddress} — click to copy & open`}
                        >
                          <Addr value={t.walletAddress} />
                        </button>
                      </Td>
                      <Td>
                        {t.niche ? <Pill tone={nicheTone(t.niche)}>{t.niche}</Pill> : <span className="text-muted-foreground">—</span>}
                      </Td>
                      <Td className="text-right">
                        <span
                          className={cn(
                            "font-semibold",
                            scoreTone(t.walletScore) === "success" && "text-success",
                            scoreTone(t.walletScore) === "warning" && "text-warning",
                            scoreTone(t.walletScore) === "muted" && "text-muted-foreground",
                          )}
                        >
                          {t.walletScore == null ? "—" : t.walletScore.toFixed(0)}
                        </span>
                      </Td>
                      <Td>
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                          {t.walletClassification ?? "—"}
                        </span>
                      </Td>
                      <Td>
                        {isBuy && <Pill tone="success">BUY</Pill>}
                        {isSell && <Pill tone="danger">SELL</Pill>}
                        {!isBuy && !isSell && <span className="text-muted-foreground">{t.side ?? "—"}</span>}
                      </Td>
                      <Td>
                        <div className="max-w-[280px] truncate">
                          <span className="text-foreground">{t.outcome ?? "—"}</span>
                          {t.marketId && (
                            <span className="ml-1 text-[10px] text-muted-foreground">
                              [{t.marketId.slice(0, 8)}…]
                            </span>
                          )}
                        </div>
                      </Td>
                      <Td className="text-right">{t.price == null ? "—" : t.price.toFixed(3)}</Td>
                      <Td className="text-right">
                        {t.usdcSize == null
                          ? "—"
                          : `$${t.usdcSize.toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
                      </Td>
                      <Td className="text-right text-muted-foreground">{relTime(t.timestamp)}</Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return <th className={cn("px-2 py-1.5 text-left font-medium", className)}>{children}</th>;
}
function Td({ children, className }: { children: React.ReactNode; className?: string }) {
  return <td className={cn("px-2 py-1.5 align-middle", className)}>{children}</td>;
}

function FilterGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-1">
      <span className="mono text-[9px] uppercase tracking-[0.2em] text-muted-foreground">// {label}</span>
      <div className="flex items-center gap-0.5">{children}</div>
    </div>
  );
}

function FilterBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "mono border px-2 py-0.5 text-[10px] uppercase tracking-wider transition-colors",
        active
          ? "border-accent bg-accent/10 text-accent"
          : "border-border text-muted-foreground hover:border-accent/50 hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}
