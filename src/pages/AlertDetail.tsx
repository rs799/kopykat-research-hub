import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "@/mock/api";
import type { ConsensusAlert } from "@/mock/data";
import { Addr, ExplainCard, Pill, SectionHeader, fmtUsd } from "@/components/kk/Primitives";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Eye, FlaskConical } from "lucide-react";

export default function AlertDetail() {
  const { id = "" } = useParams();
  const [a, setA] = useState<ConsensusAlert | undefined>();
  useEffect(() => { api.alert(id).then(setA); }, [id]);

  if (!a) return <div className="text-sm text-muted-foreground">Loading…</div>;

  const stat = (label: string, val: React.ReactNode, tone?: string) => (
    <div className="rounded border border-border bg-muted/30 p-2">
      <div className="mono text-[9px] uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className={`mono mt-0.5 text-sm ${tone ?? ""}`}>{val}</div>
    </div>
  );

  return (
    <div className="space-y-5">
      <Link to="/alerts" className="mono inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-accent">
        <ArrowLeft className="h-3 w-3" /> Back to alerts
      </Link>

      <ExplainCard title="Reading this alert">
        Below is a single consensus alert broken down: which wallets aligned, when, at what price, and any wallets
        that disagreed. KopyKat only surfaces this as research — no order is ever sent.
      </ExplainCard>

      <div className="panel p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="mono text-[10px] uppercase tracking-widest text-muted-foreground">{a.id} · {a.niche}</div>
            <h2 className="mt-1 text-xl font-semibold">{a.market}</h2>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Pill tone="accent">Side {a.side}</Pill>
              <Pill tone={a.status === "paper" ? "info" : a.status === "watch" ? "warning" : "danger"}>{a.status}</Pill>
              <Pill>Strength {a.strength}</Pill>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm"><Eye className="mr-1 h-3.5 w-3.5" /> Mark as watched</Button>
            <Button size="sm"><FlaskConical className="mr-1 h-3.5 w-3.5" /> Send to paper simulation</Button>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-6">
          {stat("Consensus", a.consensusScore.toFixed(2), "text-accent")}
          {stat("Wallets aligned", a.walletsAligned)}
          {stat("Avg wallet quality", a.avgWalletQuality.toFixed(1))}
          {stat("First price", a.firstPrice.toFixed(2))}
          {stat("Current price", a.currentPrice.toFixed(2))}
          {stat("Price moved", (a.priceMoved >= 0 ? "+" : "") + a.priceMoved.toFixed(2), a.priceMoved >= 0 ? "text-success" : "text-destructive")}
          {stat("Spread", a.spread.toFixed(3))}
          {stat("Liquidity", fmtUsd(a.liquidity))}
          {stat("Disagreement", a.disagreement)}
          {stat("Suggested max (mock)", a.suggestedMaxPrice.toFixed(2), "text-warning")}
        </div>
      </div>

      <SectionHeader title="Wallets involved" subtitle="Public addresses observed on the same side." />
      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left mono text-[10px] uppercase tracking-widest text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Wallet</th>
              <th className="px-3 py-2 text-right">Score</th>
              <th className="px-3 py-2 text-right">Niche</th>
              <th className="px-3 py-2">Observed</th>
              <th className="px-3 py-2 text-right">Price</th>
              <th className="px-3 py-2 text-right">Size</th>
              <th className="px-3 py-2 text-right">CLV hist.</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {a.wallets.map((w) => (
              <tr key={w.address} className="border-t border-border hover:bg-muted/20">
                <td className="px-3 py-2"><Addr value={w.address} /></td>
                <td className="px-3 py-2 text-right mono text-accent">{w.score.toFixed(1)}</td>
                <td className="px-3 py-2 text-right mono">{w.nicheScore.toFixed(1)}</td>
                <td className="px-3 py-2 mono text-xs text-muted-foreground">{w.observedAt}</td>
                <td className="px-3 py-2 text-right mono">{w.observedPrice.toFixed(2)}</td>
                <td className="px-3 py-2 text-right mono">{fmtUsd(w.size)}</td>
                <td className={`px-3 py-2 text-right mono ${w.clvHistory >= 0 ? "text-success" : "text-destructive"}`}>
                  {(w.clvHistory * 100).toFixed(2)}%
                </td>
                <td className="px-3 py-2"><Pill>{w.status}</Pill></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="panel p-4">
          <SectionHeader title="Disagreement" subtitle="Wallets on the other side of the same market." />
          {a.disagreementDetail.length === 0 ? (
            <div className="text-sm text-muted-foreground">No disagreement recorded (mock).</div>
          ) : (
            <ul className="space-y-2">
              {a.disagreementDetail.map((d, i) => (
                <li key={i} className="flex items-center justify-between rounded border border-border bg-muted/30 p-2 text-xs">
                  <Addr value={d.address} />
                  <Pill tone="warning">{d.side}</Pill>
                  <span className="mono">{fmtUsd(d.size)}</span>
                  <span className="text-muted-foreground">{d.note}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="panel p-4">
          <SectionHeader title="Reason" subtitle="Why KopyKat set this status." />
          <p className="text-sm text-muted-foreground">{a.reason}</p>
          <div className="mono mt-3 rounded border border-warning/40 bg-warning/10 p-2 text-[10px] uppercase tracking-widest text-warning">
            Research only · Paper mode · No real orders
          </div>
        </div>
      </div>
    </div>
  );
}
