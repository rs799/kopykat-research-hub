import { useEffect, useMemo, useState } from "react";
import { api } from "@/mock/api";
import type { NicheKey, RankedWallet } from "@/mock/data";
import { Addr, ExplainCard, Pill, SectionHeader, fmtPct, fmtUsd } from "@/components/kk/Primitives";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const nicheOptions: { key: NicheKey; name: string }[] = [
  { key: "crypto", name: "Crypto" },
  { key: "sports", name: "Sports" },
  { key: "macro", name: "Macro" },
  { key: "tech", name: "Tech & Culture" },
  { key: "global", name: "Global Events" },
];

function ScoreBar({ label, value, max = 100, negative = false }: { label: string; value: number; max?: number; negative?: boolean }) {
  const pct = Math.min(100, Math.max(0, (Math.abs(value) / max) * 100));
  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className={`mono text-xs ${negative ? "text-destructive" : "text-foreground"}`}>
          {value > 0 && !negative ? "+" : ""}
          {value.toFixed(1)}
        </span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded bg-muted">
        <div
          className={`h-full rounded ${negative ? "bg-destructive/70" : "bg-accent"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function Rankings() {
  const [niche, setNiche] = useState<NicheKey>("crypto");
  const [rows, setRows] = useState<RankedWallet[]>([]);
  const [selected, setSelected] = useState<RankedWallet | null>(null);

  useEffect(() => {
    api.walletRankings(niche).then((r) => {
      setRows(r);
      setSelected(r[0] ?? null);
    });
  }, [niche]);

  const nicheLabel = useMemo(() => nicheOptions.find((n) => n.key === niche)?.name ?? niche, [niche]);

  return (
    <div className="space-y-5">
      <ExplainCard title="How are wallets ranked?">
        Each wallet gets a niche-specific score built from mock components: Bayesian ROI, closing-line value (CLV),
        sample size, drawdown control, liquidity, timing edge, recency, and penalties. Higher score = KopyKat treats
        that wallet as more informative for that niche. All numbers on this page are mock.
      </ExplainCard>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeader title={`Top wallets — ${nicheLabel}`} subtitle="Ranked on mock in-niche history." />
        <Select value={niche} onValueChange={(v) => setNiche(v as NicheKey)}>
          <SelectTrigger className="h-8 w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {nicheOptions.map((n) => (
              <SelectItem key={n.key} value={n.key}>
                {n.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="panel overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left mono text-[10px] uppercase tracking-widest text-muted-foreground">
              <tr>
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Wallet</th>
                <th className="px-3 py-2 text-right">Niche</th>
                <th className="px-3 py-2 text-right">Global</th>
                <th className="px-3 py-2 text-right">PnL</th>
                <th className="px-3 py-2 text-right">ROI</th>
                <th className="px-3 py-2 text-right">CLV</th>
                <th className="px-3 py-2 text-right">Sample</th>
                <th className="px-3 py-2 text-right">DD</th>
                <th className="px-3 py-2">Specialty</th>
                <th className="px-3 py-2">Recency</th>
                <th className="px-3 py-2">Flags</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((w) => {
                const active = selected?.address === w.address;
                return (
                  <tr
                    key={w.address}
                    onClick={() => setSelected(w)}
                    className={`cursor-pointer border-t border-border hover:bg-muted/20 ${
                      active ? "bg-accent/10" : ""
                    }`}
                  >
                    <td className="px-3 py-2 mono text-muted-foreground">{w.rank}</td>
                    <td className="px-3 py-2"><Addr value={w.address} /></td>
                    <td className="px-3 py-2 text-right mono text-accent">{w.nicheScore.toFixed(1)}</td>
                    <td className="px-3 py-2 text-right mono">{w.globalScore.toFixed(1)}</td>
                    <td className={`px-3 py-2 text-right mono ${w.realizedPnl >= 0 ? "text-success" : "text-destructive"}`}>
                      {fmtUsd(w.realizedPnl)}
                    </td>
                    <td className={`px-3 py-2 text-right mono ${w.roi >= 0 ? "text-success" : "text-destructive"}`}>
                      {fmtPct(w.roi)}
                    </td>
                    <td className="px-3 py-2 text-right mono">{w.clvScore.toFixed(1)}</td>
                    <td className="px-3 py-2 text-right mono">{w.sampleSize}</td>
                    <td className="px-3 py-2 text-right mono text-destructive">-{fmtPct(w.drawdown)}</td>
                    <td className="px-3 py-2"><Pill>{w.specialty}</Pill></td>
                    <td className="px-3 py-2 mono text-xs text-muted-foreground">{w.recency}d</td>
                    <td className="px-3 py-2">
                      {w.flags.length ? <Pill tone="warning">{w.flags[0]}</Pill> : <span className="text-muted-foreground">—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="panel p-4">
          <div className="mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Selected wallet</div>
          {selected ? (
            <>
              <div className="mt-1 flex items-center gap-2">
                <Addr value={selected.address} />
                <Pill tone="accent">Rank #{selected.rank}</Pill>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <Pill tone="success">Niche {selected.nicheScore.toFixed(1)}</Pill>
                <Pill>Global {selected.globalScore.toFixed(1)}</Pill>
                <Pill tone="info">{selected.specialty}</Pill>
              </div>
              <div className="mt-4 space-y-3">
                <ScoreBar label="Bayesian ROI" value={selected.breakdown.bayesianRoi} />
                <ScoreBar label="CLV" value={selected.breakdown.clv} />
                <ScoreBar label="Sample size" value={selected.breakdown.sampleSize} />
                <ScoreBar label="Drawdown control" value={selected.breakdown.drawdownControl} />
                <ScoreBar label="Liquidity adj." value={selected.breakdown.liquidityAdj} />
                <ScoreBar label="Timing edge" value={selected.breakdown.timingEdge} />
                <ScoreBar label="Recency" value={selected.breakdown.recency} />
                <ScoreBar label="Penalties" value={selected.breakdown.penalties} negative />
              </div>
              <div className="mono mt-4 rounded border border-border bg-muted/30 p-2 text-[10px] uppercase tracking-widest text-muted-foreground">
                All score components are mock — for prototyping only.
              </div>
            </>
          ) : (
            <div className="text-sm text-muted-foreground">Select a wallet to see its breakdown.</div>
          )}
        </div>
      </div>
    </div>
  );
}
