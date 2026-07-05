import { useEffect, useMemo, useState } from "react";
import { api } from "@/mock/api";
import type { Backtest } from "@/mock/data";
import { equityCurve } from "@/mock/data";
import { ExplainCard, Pill, SectionHeader, StatCard, fmtPct } from "@/components/kk/Primitives";

function EquityChart() {
  const w = 800, h = 180, pad = 16;
  const xs = equityCurve.map((d) => d.day);
  const ys = equityCurve.map((d) => d.equity);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const px = (x: number) => pad + ((x - xs[0]) / (xs[xs.length - 1] - xs[0])) * (w - pad * 2);
  const py = (y: number) => h - pad - ((y - minY) / (maxY - minY || 1)) * (h - pad * 2);
  const d = equityCurve.map((p, i) => `${i === 0 ? "M" : "L"}${px(p.day).toFixed(1)},${py(p.equity).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-44 w-full">
      <defs>
        <linearGradient id="eqfill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity="0.35" />
          <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${d} L ${px(xs[xs.length - 1])},${h - pad} L ${px(xs[0])},${h - pad} Z`} fill="url(#eqfill)" />
      <path d={d} fill="none" stroke="hsl(var(--accent))" strokeWidth="1.5" />
    </svg>
  );
}

export default function Backtests() {
  const [rows, setRows] = useState<Backtest[]>([]);
  useEffect(() => { api.backtests().then(setRows); }, []);

  const summary = useMemo(() => {
    if (!rows.length) return null;
    const totalRuns = rows.reduce((s, r) => s + r.runs, 0);
    const best = rows.reduce((a, b) => (b.roi > a.roi ? b : a));
    return {
      totalRuns,
      bestNiche: best.niche,
      bestStrategy: best.strategy,
      roi: best.roi,
      maxDrawdown: Math.min(...rows.map(r => r.maxDrawdown)),
      fillRate: rows.reduce((s, r) => s + r.fillRate, 0) / rows.length,
      missedFillRate: rows.reduce((s, r) => s + r.missedFillRate, 0) / rows.length,
      avgAlertStrength: rows.reduce((s, r) => s + r.avgAlertStrength, 0) / rows.length,
    };
  }, [rows]);

  const rejectReasons = [
    { name: "Sample too small", pct: 0.32 },
    { name: "Negative CLV", pct: 0.24 },
    { name: "Low liquidity", pct: 0.18 },
    { name: "Disagreement high", pct: 0.14 },
    { name: "Regime shift", pct: 0.12 },
  ];

  return (
    <div className="space-y-5">
      <ExplainCard title="What is a backtest?">
        A backtest replays the mock historical stream and simulates what KopyKat's alert + paper-sim engine would have
        produced. The numbers on this page are all fabricated and intended only for UI review.
      </ExplainCard>

      {summary && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatCard label="Total runs" value={summary.totalRuns} />
          <StatCard label="Best niche" value={summary.bestNiche} tone="info" />
          <StatCard label="Best strategy ROI" value={fmtPct(summary.roi)} tone="success" hint={summary.bestStrategy} />
          <StatCard label="Worst drawdown" value={fmtPct(summary.maxDrawdown)} tone="danger" />
          <StatCard label="Fill rate" value={fmtPct(summary.fillRate)} tone="info" />
          <StatCard label="Missed fill rate" value={fmtPct(summary.missedFillRate)} tone="warning" />
          <StatCard label="Avg alert strength" value={summary.avgAlertStrength.toFixed(1)} />
          <StatCard label="Strategies tested" value={rows.length} />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <div className="panel p-4">
          <SectionHeader title="Equity curve (mock)" subtitle="60-day paper equity progression." />
          <EquityChart />
        </div>
        <div className="panel p-4">
          <SectionHeader title="Rejection reasons" subtitle="Why mock alerts were dropped." />
          <div className="space-y-2">
            {rejectReasons.map(r => (
              <div key={r.name}>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{r.name}</span>
                  <span className="mono text-foreground">{fmtPct(r.pct)}</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded bg-muted">
                  <div className="h-full bg-warning" style={{ width: `${r.pct * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <SectionHeader title="Performance by niche & strategy" />
      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left mono text-[10px] uppercase tracking-widest text-muted-foreground">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Niche</th>
              <th className="px-3 py-2">Strategy</th>
              <th className="px-3 py-2 text-right">ROI</th>
              <th className="px-3 py-2 text-right">Max DD</th>
              <th className="px-3 py-2 text-right">Fill</th>
              <th className="px-3 py-2 text-right">Missed</th>
              <th className="px-3 py-2 text-right">Avg strength</th>
              <th className="px-3 py-2 text-right">Runs</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.id} className="border-t border-border hover:bg-muted/20">
                <td className="px-3 py-2 mono text-xs">{r.id}</td>
                <td className="px-3 py-2"><Pill>{r.niche}</Pill></td>
                <td className="px-3 py-2 mono text-xs">{r.strategy}</td>
                <td className={`px-3 py-2 text-right mono ${r.roi >= 0 ? "text-success" : "text-destructive"}`}>{fmtPct(r.roi)}</td>
                <td className="px-3 py-2 text-right mono text-destructive">{fmtPct(r.maxDrawdown)}</td>
                <td className="px-3 py-2 text-right mono">{fmtPct(r.fillRate)}</td>
                <td className="px-3 py-2 text-right mono">{fmtPct(r.missedFillRate)}</td>
                <td className="px-3 py-2 text-right mono">{r.avgAlertStrength.toFixed(1)}</td>
                <td className="px-3 py-2 text-right mono">{r.runs}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
