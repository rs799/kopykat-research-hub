import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/mock/api";
import type { ConsensusAlert } from "@/mock/data";
import { ExplainCard, Pill, SectionHeader, fmtUsd } from "@/components/kk/Primitives";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const statusTone = (s: ConsensusAlert["status"]) =>
  ({ watch: "warning", paper: "info", rejected: "danger" } as const)[s];

export default function Alerts() {
  const [rows, setRows] = useState<ConsensusAlert[]>([]);
  const [niche, setNiche] = useState<string>("all");
  const [status, setStatus] = useState<string>("all");
  const [minStrength, setMin] = useState(0);
  const [q, setQ] = useState("");

  useEffect(() => { api.alerts().then(setRows); }, []);

  const filtered = useMemo(
    () => rows.filter(a =>
      (niche === "all" || a.niche === niche) &&
      (status === "all" || a.status === status) &&
      a.strength >= minStrength &&
      (q === "" || a.market.toLowerCase().includes(q.toLowerCase()))
    ),
    [rows, niche, status, minStrength, q]
  );

  return (
    <div className="space-y-5">
      <ExplainCard title="What is a consensus alert?">
        When several top-ranked wallets in the same niche appear to take the same side of the same market at similar
        times, KopyKat raises a consensus alert. It's a research signal — not a trade instruction. All alerts here are mock.
      </ExplainCard>

      <div className="panel flex flex-wrap items-center gap-2 p-3">
        <Input placeholder="Search market…" value={q} onChange={(e) => setQ(e.target.value)} className="h-8 w-56" />
        <Select value={niche} onValueChange={setNiche}>
          <SelectTrigger className="h-8 w-40"><SelectValue placeholder="Niche" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All niches</SelectItem>
            <SelectItem value="crypto">Crypto</SelectItem>
            <SelectItem value="sports">Sports</SelectItem>
            <SelectItem value="macro">Macro</SelectItem>
            <SelectItem value="tech">Tech</SelectItem>
            <SelectItem value="global">Global</SelectItem>
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="h-8 w-40"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="watch">Watch</SelectItem>
            <SelectItem value="paper">Paper Sim</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
          </SelectContent>
        </Select>
        <div className="flex items-center gap-2">
          <span className="mono text-[10px] uppercase tracking-widest text-muted-foreground">Min strength</span>
          <Input type="number" value={minStrength} onChange={(e) => setMin(Number(e.target.value) || 0)} className="h-8 w-20" />
        </div>
      </div>

      <SectionHeader title="Consensus alerts" subtitle={`${filtered.length} of ${rows.length} shown`} />
      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left mono text-[10px] uppercase tracking-widest text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Strength</th>
              <th className="px-3 py-2">Niche</th>
              <th className="px-3 py-2">Market</th>
              <th className="px-3 py-2">Side</th>
              <th className="px-3 py-2 text-right">Wallets</th>
              <th className="px-3 py-2 text-right">Avg Score</th>
              <th className="px-3 py-2 text-right">First</th>
              <th className="px-3 py-2 text-right">Now</th>
              <th className="px-3 py-2 text-right">Δ</th>
              <th className="px-3 py-2 text-right">Spread</th>
              <th className="px-3 py-2 text-right">Liquidity</th>
              <th className="px-3 py-2 text-right">Disagree</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Reason</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(a => (
              <tr key={a.id} className="border-t border-border hover:bg-muted/20">
                <td className="px-3 py-2">
                  <Link to={`/alerts/${a.id}`} className="mono text-accent hover:underline">{a.strength}</Link>
                </td>
                <td className="px-3 py-2"><Pill>{a.niche}</Pill></td>
                <td className="px-3 py-2">
                  <Link to={`/alerts/${a.id}`} className="hover:text-accent">{a.market}</Link>
                </td>
                <td className="px-3 py-2 mono">{a.side}</td>
                <td className="px-3 py-2 text-right mono">{a.walletsAligned}</td>
                <td className="px-3 py-2 text-right mono">{a.avgWalletScore.toFixed(1)}</td>
                <td className="px-3 py-2 text-right mono">{a.firstPrice.toFixed(2)}</td>
                <td className="px-3 py-2 text-right mono">{a.currentPrice.toFixed(2)}</td>
                <td className={`px-3 py-2 text-right mono ${a.priceMoved >= 0 ? "text-success" : "text-destructive"}`}>
                  {a.priceMoved >= 0 ? "+" : ""}{a.priceMoved.toFixed(2)}
                </td>
                <td className="px-3 py-2 text-right mono">{a.spread.toFixed(3)}</td>
                <td className="px-3 py-2 text-right mono">{fmtUsd(a.liquidity)}</td>
                <td className="px-3 py-2 text-right mono">{a.disagreement}</td>
                <td className="px-3 py-2"><Pill tone={statusTone(a.status)}>{a.status}</Pill></td>
                <td className="px-3 py-2 text-xs text-muted-foreground">{a.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
