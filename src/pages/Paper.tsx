import { useEffect, useState } from "react";
import { api } from "@/mock/api";
import { ExplainCard, Pill, SectionHeader, StatCard, fmtPct, fmtUsd } from "@/components/kk/Primitives";
import { AlertTriangle } from "lucide-react";

export default function Paper() {
  const [d, setD] = useState<Awaited<ReturnType<typeof api.paperSimulation>> | null>(null);
  useEffect(() => { api.paperSimulation().then(setD); }, []);
  if (!d) return null;

  return (
    <div className="space-y-5">
      <div className="panel flex items-center gap-3 border-warning/50 p-3">
        <AlertTriangle className="h-5 w-5 text-warning" />
        <div className="text-sm">
          <span className="mono text-warning">SIMULATION ONLY.</span>{" "}
          <span className="text-muted-foreground">No real orders are ever placed. All balances, fills, and PnL are fabricated.</span>
        </div>
      </div>

      <ExplainCard title="What is Paper Simulation?">
        When a consensus alert clears KopyKat's mock thresholds, it is routed here to a simulated portfolio. This lets
        you see how the alert would have performed <em>hypothetically</em>. Nothing here touches real funds.
      </ExplainCard>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Paper balance" value={fmtUsd(d.balance)} />
        <StatCard label="Open positions" value={d.openPositions} tone="info" />
        <StatCard label="Realized PnL" value={fmtUsd(d.realizedPnl)} tone="success" />
        <StatCard label="Unrealized PnL" value={fmtUsd(d.unrealizedPnl)} tone="success" />
        <StatCard label="Win rate" value={fmtPct(d.winRate)} />
        <StatCard label="Max drawdown" value={fmtPct(d.maxDrawdown)} tone="danger" />
        <StatCard label="Fill rate" value={fmtPct(d.fillRate)} tone="info" />
        <StatCard label="Missed fill rate" value={fmtPct(d.missedFillRate)} tone="warning" />
      </div>

      <SectionHeader title="Simulated positions" />
      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left mono text-[10px] uppercase tracking-widest text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Market</th>
              <th className="px-3 py-2">Side</th>
              <th className="px-3 py-2 text-right">Avg</th>
              <th className="px-3 py-2 text-right">Size</th>
              <th className="px-3 py-2 text-right">Mark</th>
              <th className="px-3 py-2 text-right">Unrealized</th>
            </tr>
          </thead>
          <tbody>
            {d.positions.map((p, i) => (
              <tr key={i} className="border-t border-border hover:bg-muted/20">
                <td className="px-3 py-2">{p.market}</td>
                <td className="px-3 py-2"><Pill>{p.side}</Pill></td>
                <td className="px-3 py-2 text-right mono">{p.avgPrice.toFixed(2)}</td>
                <td className="px-3 py-2 text-right mono">{fmtUsd(p.size)}</td>
                <td className="px-3 py-2 text-right mono">{p.markPrice.toFixed(2)}</td>
                <td className={`px-3 py-2 text-right mono ${p.unrealized >= 0 ? "text-success" : "text-destructive"}`}>
                  {fmtUsd(p.unrealized)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <SectionHeader title="Simulated orders & fills" />
      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left mono text-[10px] uppercase tracking-widest text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Market</th>
              <th className="px-3 py-2">Side</th>
              <th className="px-3 py-2 text-right">Price</th>
              <th className="px-3 py-2 text-right">Size</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Alert</th>
            </tr>
          </thead>
          <tbody>
            {d.orders.map((o) => (
              <tr key={o.id} className="border-t border-border hover:bg-muted/20">
                <td className="px-3 py-2 mono text-xs text-muted-foreground">{o.time}</td>
                <td className="px-3 py-2 mono text-xs">{o.id}</td>
                <td className="px-3 py-2">{o.market}</td>
                <td className="px-3 py-2"><Pill>{o.side}</Pill></td>
                <td className="px-3 py-2 text-right mono">{o.price.toFixed(2)}</td>
                <td className="px-3 py-2 text-right mono">{fmtUsd(o.size)}</td>
                <td className="px-3 py-2">
                  <Pill tone={o.status === "filled" ? "success" : o.status === "partial" ? "warning" : "danger"}>
                    {o.status}
                  </Pill>
                </td>
                <td className="px-3 py-2 mono text-xs text-accent">{o.linkedAlert}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
