import { useEffect, useMemo, useState } from "react";
import { api } from "@/mock/api";
import type { NicheKey, Wallet } from "@/mock/data";
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

const statusTone = (s: Wallet["status"]) =>
  ({ qualified: "success", watch: "warning", rejected: "danger", suspicious: "danger" } as const)[s];

export default function WalletDiscovery() {
  const [niche, setNiche] = useState<NicheKey>("crypto");
  const [wallets, setWallets] = useState<Wallet[]>([]);
  useEffect(() => {
    api.walletDiscovery(niche).then(setWallets);
  }, [niche]);

  const stats = useMemo(() => {
    const qualified = wallets.filter((w) => w.status === "qualified").length;
    const watching = wallets.filter((w) => w.status === "watch").length;
    const rejected = wallets.filter((w) => w.status === "rejected").length;
    return { qualified, watching, rejected };
  }, [wallets]);

  return (
    <div className="space-y-5">
      <ExplainCard title="What is Wallet Discovery?">
        These are <strong>public wallet addresses</strong> observed acting in the chosen niche. KopyKat only reads
        public activity — it does not have private access to any wallet, and it never sends transactions.
      </ExplainCard>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionHeader title="Discovered wallets" subtitle="Filtered by niche. All numbers are mock." />
        <div className="flex items-center gap-2">
          <span className="mono text-[10px] uppercase tracking-widest text-muted-foreground">Niche</span>
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
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="panel p-3">
          <div className="mono text-[10px] uppercase tracking-widest text-muted-foreground">Qualified</div>
          <div className="mono mt-1 text-xl text-success">{stats.qualified}</div>
        </div>
        <div className="panel p-3">
          <div className="mono text-[10px] uppercase tracking-widest text-muted-foreground">Watch</div>
          <div className="mono mt-1 text-xl text-warning">{stats.watching}</div>
        </div>
        <div className="panel p-3">
          <div className="mono text-[10px] uppercase tracking-widest text-muted-foreground">Rejected</div>
          <div className="mono mt-1 text-xl text-destructive">{stats.rejected}</div>
        </div>
      </div>

      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left mono text-[10px] uppercase tracking-widest text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Wallet</th>
              <th className="px-3 py-2">Niche</th>
              <th className="px-3 py-2 text-right">Markets</th>
              <th className="px-3 py-2 text-right">Resolved</th>
              <th className="px-3 py-2 text-right">PnL (mock)</th>
              <th className="px-3 py-2 text-right">ROI</th>
              <th className="px-3 py-2 text-right">CLV</th>
              <th className="px-3 py-2 text-right">Sample</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Reason</th>
            </tr>
          </thead>
          <tbody>
            {wallets.map((w) => (
              <tr key={w.address} className="border-t border-border hover:bg-muted/20">
                <td className="px-3 py-2"><Addr value={w.address} /></td>
                <td className="px-3 py-2"><Pill>{w.niche}</Pill></td>
                <td className="px-3 py-2 text-right mono">{w.marketsObserved}</td>
                <td className="px-3 py-2 text-right mono">{w.resolvedObservations}</td>
                <td className={`px-3 py-2 text-right mono ${w.realizedPnl >= 0 ? "text-success" : "text-destructive"}`}>
                  {fmtUsd(w.realizedPnl)}
                </td>
                <td className={`px-3 py-2 text-right mono ${w.roi >= 0 ? "text-success" : "text-destructive"}`}>
                  {fmtPct(w.roi)}
                </td>
                <td className="px-3 py-2 text-right mono">{fmtPct(w.clv, 2)}</td>
                <td className="px-3 py-2 text-right mono">{w.sampleSize}</td>
                <td className="px-3 py-2"><Pill tone={statusTone(w.status)}>{w.status}</Pill></td>
                <td className="px-3 py-2 text-xs text-muted-foreground">{w.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
