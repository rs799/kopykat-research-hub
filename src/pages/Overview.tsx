import { useEffect, useState } from "react";
import { ArrowRight, Radar, Users, Trophy, AlertTriangle, FlaskConical, Beaker } from "lucide-react";
import { api } from "@/mock/api";
import { ExplainCard, StatCard, SectionHeader, fmtUsd } from "@/components/kk/Primitives";

const flow = [
  { key: "niche", label: "Niche", icon: Radar },
  { key: "discovery", label: "Wallet Discovery", icon: Users },
  { key: "rank", label: "Wallet Ranking", icon: Trophy },
  { key: "alert", label: "Consensus Alert", icon: AlertTriangle },
  { key: "paper", label: "Paper Simulation", icon: FlaskConical },
  { key: "backtest", label: "Backtest", icon: Beaker },
];

export default function Overview() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.overview>> | null>(null);
  useEffect(() => {
    api.overview().then(setData);
  }, []);

  return (
    <div className="space-y-5">
      <ExplainCard title="What is KopyKat?">
        A private research terminal for organizing <em>public</em> Polymarket wallet activity. You pick a niche,
        KopyKat surfaces public wallets active there, ranks them on mock historical stats, and flags moments where
        several top-ranked wallets appear aligned on the same market. Everything on this dashboard is fake.
      </ExplainCard>

      <div className="panel p-3">
        <SectionHeader
          title="Research pipeline"
          subtitle="Passive: observes, ranks, flags. Never trades."
        />
        <div className="flex flex-wrap items-stretch gap-1">
          {flow.map((step, i) => (
            <div key={step.key} className="flex items-center gap-1">
              <div className="flex min-w-[130px] items-center gap-2 border border-border bg-muted/20 px-2 py-1">
                <step.icon className="h-3 w-3 text-accent" />
                <div className="leading-tight">
                  <div className="mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
                    {String(i + 1).padStart(2, "0")}
                  </div>
                  <div className="mono text-[11px] uppercase tracking-wider">{step.label}</div>
                </div>
              </div>
              {i < flow.length - 1 && <ArrowRight className="h-3 w-3 text-muted-foreground" />}
            </div>
          ))}
        </div>
      </div>

      {data && (
        <>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-5">
            <StatCard label="Active niches" value={data.activeNiches} />
            <StatCard label="Discovered wallets" value={data.discoveredWallets} tone="info" />
            <StatCard label="Qualified wallets" value={data.qualifiedWallets} tone="success" />
            <StatCard label="Consensus alerts" value={data.consensusAlerts} tone="warning" />
            <StatCard label="Rejected alerts" value={data.rejectedAlerts} tone="danger" />
          </div>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            <StatCard label="Mock paper PnL" value={fmtUsd(data.paperPnl)} tone="success" hint="Simulated only" />
            <StatCard label="Parser warnings" value={data.parserWarnings} tone="warning" />
            <StatCard label="Backend status" value={data.backendStatus} tone="info" hint="No real backend" />
            <StatCard label="Mode" value={data.mode} tone="warning" hint="Paper locked ON" />
          </div>
        </>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
            <StatCard label="Active niches" value={data.activeNiches} />
            <StatCard label="Discovered wallets" value={data.discoveredWallets} tone="info" />
            <StatCard label="Qualified wallets" value={data.qualifiedWallets} tone="success" />
            <StatCard label="Consensus alerts" value={data.consensusAlerts} tone="warning" />
            <StatCard label="Rejected alerts" value={data.rejectedAlerts} tone="danger" />
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatCard label="Mock paper PnL" value={fmtUsd(data.paperPnl)} tone="success" hint="Simulated only" />
            <StatCard label="Parser warnings" value={data.parserWarnings} tone="warning" />
            <StatCard label="Backend status" value={data.backendStatus} tone="info" hint="No real backend attached" />
            <StatCard label="Mode" value={data.mode} tone="warning" hint="Paper mode is locked ON" />
          </div>
        </>
      )}
    </div>
  );
}
