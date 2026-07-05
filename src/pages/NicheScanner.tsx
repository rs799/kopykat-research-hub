import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/mock/api";
import type { Niche } from "@/mock/data";
import { ExplainCard, Pill, SectionHeader, fmtUsd } from "@/components/kk/Primitives";
import { ChevronRight } from "lucide-react";

export default function NicheScanner() {
  const [niches, setNiches] = useState<Niche[]>([]);
  useEffect(() => {
    api.niches().then(setNiches);
  }, []);

  return (
    <div className="space-y-5">
      <ExplainCard title="What is a niche?">
        A niche is a category of markets — e.g. Crypto or Sports. KopyKat scans each niche independently because a
        wallet that is sharp on football may be random on macro. Coverage numbers below are mock.
      </ExplainCard>

      <SectionHeader title="Niches" subtitle="Coverage, wallet counts, and warnings per niche." />
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {niches.map((n) => (
          <Link key={n.key} to="/discovery" className="panel group block p-4 transition-colors hover:border-accent/50">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-semibold tracking-tight">{n.name}</h3>
                  <Pill
                    tone={n.status === "healthy" ? "success" : n.status === "degraded" ? "warning" : "danger"}
                  >
                    {n.status}
                  </Pill>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{n.description}</p>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2 text-center">
              {[
                ["Markets", n.markets],
                ["Discovered", n.discoveredWallets],
                ["Qualified", n.qualifiedWallets],
                ["Avg Liq", fmtUsd(n.avgLiquidity)],
                ["Alerts", n.alerts],
                ["Warnings", n.warnings],
              ].map(([label, val]) => (
                <div key={String(label)} className="rounded border border-border bg-muted/30 p-2">
                  <div className="mono text-[9px] uppercase tracking-widest text-muted-foreground">{label}</div>
                  <div className="mono mt-0.5 text-sm text-foreground">{val}</div>
                </div>
              ))}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
