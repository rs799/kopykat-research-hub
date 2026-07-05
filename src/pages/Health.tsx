import { useEffect, useState } from "react";
import { api } from "@/mock/api";
import { Addr, ExplainCard, Pill, SectionHeader, StatCard } from "@/components/kk/Primitives";

export default function Health() {
  const [d, setD] = useState<Awaited<ReturnType<typeof api.dataHealth>> | null>(null);
  useEffect(() => { api.dataHealth().then(setD); }, []);
  if (!d) return null;

  return (
    <div className="space-y-5">
      <ExplainCard title="Why does data health matter?">
        A ranking is only as good as the data behind it. This page shows mock parser warnings, endpoint status, and
        lifecycle events so you can tell whether the numbers on other pages should be trusted.
      </ExplainCard>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Raw activity rows" value={d.rawRows.toLocaleString()} />
        <StatCard label="Lifecycle events" value={d.lifecycleEvents.toLocaleString()} tone="info" />
        <StatCard label="Unresolved issues" value={d.unresolvedIssues} tone="warning" />
        <StatCard label="Endpoints" value={d.endpoints.length} />
      </div>

      <SectionHeader title="Endpoints (mock)" />
      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left mono text-[10px] uppercase tracking-widest text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Endpoint</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Last ingestion</th>
            </tr>
          </thead>
          <tbody>
            {d.endpoints.map(e => (
              <tr key={e.name} className="border-t border-border">
                <td className="px-3 py-2 mono">{e.name}</td>
                <td className="px-3 py-2"><Pill tone={e.status === "ok" ? "success" : "warning"}>{e.status}</Pill></td>
                <td className="px-3 py-2 mono text-xs text-muted-foreground">{e.lastIngestion}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <SectionHeader title="Parser warnings" subtitle="Rows where the mock parser had to compensate." />
      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left mono text-[10px] uppercase tracking-widest text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Timestamp</th>
              <th className="px-3 py-2">Endpoint</th>
              <th className="px-3 py-2">Wallet</th>
              <th className="px-3 py-2">Severity</th>
              <th className="px-3 py-2">Warning</th>
              <th className="px-3 py-2">Raw</th>
              <th className="px-3 py-2">Parsed</th>
              <th className="px-3 py-2">Message</th>
            </tr>
          </thead>
          <tbody>
            {d.warnings.map((w, i) => (
              <tr key={i} className="border-t border-border hover:bg-muted/20">
                <td className="px-3 py-2 mono text-xs text-muted-foreground">{w.timestamp}</td>
                <td className="px-3 py-2 mono text-xs">{w.endpoint}</td>
                <td className="px-3 py-2"><Addr value={w.wallet} /></td>
                <td className="px-3 py-2">
                  <Pill tone={w.severity === "high" ? "danger" : w.severity === "med" ? "warning" : "muted"}>
                    {w.severity}
                  </Pill>
                </td>
                <td className="px-3 py-2 text-xs">{w.warning}</td>
                <td className="px-3 py-2 mono text-xs text-muted-foreground">{w.rawField}</td>
                <td className="px-3 py-2 mono text-xs">{w.parsedField}</td>
                <td className="px-3 py-2 text-xs text-muted-foreground">{w.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
