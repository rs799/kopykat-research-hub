import { useEffect, useMemo, useState } from "react";
import { api } from "@/mock/api";
import type { NicheKey, Wallet } from "@/mock/data";
import { Addr, ExplainCard, Pill, SectionHeader } from "@/components/kk/Primitives";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

type Tab = "all" | "tracked" | "top" | "rejected" | "suspicious";
const tabs: { key: Tab; label: string }[] = [
  { key: "all", label: "All" },
  { key: "tracked", label: "Tracked" },
  { key: "top", label: "Top by niche" },
  { key: "rejected", label: "Rejected" },
  { key: "suspicious", label: "Suspicious" },
];

export default function Wallets() {
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [tab, setTab] = useState<Tab>("all");
  const [addr, setAddr] = useState("");
  const [niche, setNiche] = useState<NicheKey>("crypto");

  const load = () => api.wallets().then(setWallets);
  useEffect(() => { load(); }, []);

  const shown = useMemo(() => {
    switch (tab) {
      case "tracked": return wallets.filter(w => w.status === "qualified" || w.status === "watch");
      case "top": return [...wallets].sort((a, b) => b.roi - a.roi).slice(0, 20);
      case "rejected": return wallets.filter(w => w.status === "rejected");
      case "suspicious": return wallets.filter(w => w.status === "suspicious");
      default: return wallets;
    }
  }, [wallets, tab]);

  const add = async () => {
    if (!/^0x[0-9a-fA-F]{40}$/.test(addr)) { toast.error("Invalid public address (0x + 40 hex chars)"); return; }
    await api.addWallet(addr.toLowerCase(), niche);
    setAddr("");
    toast.success("Wallet added (mock, public address only)");
    load();
  };
  const remove = async (address: string) => {
    await api.removeWallet(address);
    toast("Wallet removed");
    load();
  };

  return (
    <div className="space-y-5">
      <ExplainCard title="What is stored here?">
        Only <strong>public wallet addresses</strong> KopyKat has ever surfaced or that you added manually. No private
        keys, no seed phrases, no wallet connect — this is a read-only research index.
      </ExplainCard>

      <div className="panel p-4">
        <SectionHeader title="Add wallet (mock)" subtitle="Public addresses only. 0x + 40 hex characters." />
        <div className="flex flex-wrap items-center gap-2">
          <Input placeholder="0x…" value={addr} onChange={(e) => setAddr(e.target.value)} className="h-9 w-96 mono" />
          <Select value={niche} onValueChange={(v) => setNiche(v as NicheKey)}>
            <SelectTrigger className="h-9 w-40"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="crypto">Crypto</SelectItem>
              <SelectItem value="sports">Sports</SelectItem>
              <SelectItem value="macro">Macro</SelectItem>
              <SelectItem value="tech">Tech</SelectItem>
              <SelectItem value="global">Global</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={add}>Add wallet</Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-border">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`mono px-3 py-1.5 text-[11px] uppercase tracking-widest ${
              tab === t.key ? "text-accent border-b-2 border-accent" : "text-muted-foreground hover:text-foreground"
            }`}
          >{t.label}</button>
        ))}
      </div>

      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left mono text-[10px] uppercase tracking-widest text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Wallet</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Niches observed</th>
              <th className="px-3 py-2">First seen</th>
              <th className="px-3 py-2">Last seen</th>
              <th className="px-3 py-2 text-right">Score</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Tags</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {shown.map(w => (
              <tr key={w.address} className="border-t border-border hover:bg-muted/20">
                <td className="px-3 py-2"><Addr value={w.address} /></td>
                <td className="px-3 py-2 mono text-xs text-muted-foreground">{w.source}</td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1">
                    {w.nichesObserved.map(n => <Pill key={n}>{n}</Pill>)}
                  </div>
                </td>
                <td className="px-3 py-2 mono text-xs text-muted-foreground">{w.firstSeen}</td>
                <td className="px-3 py-2 mono text-xs text-muted-foreground">{w.lastSeen}</td>
                <td className="px-3 py-2 text-right mono">{(w.roi * 100).toFixed(1)}</td>
                <td className="px-3 py-2">
                  <Pill tone={w.status === "qualified" ? "success" : w.status === "watch" ? "warning" : "danger"}>
                    {w.status}
                  </Pill>
                </td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1">
                    {w.tags.map(t => <Pill key={t}>{t}</Pill>)}
                  </div>
                </td>
                <td className="px-3 py-2 text-right">
                  <Button variant="ghost" size="sm" onClick={() => remove(w.address)}>Remove</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
