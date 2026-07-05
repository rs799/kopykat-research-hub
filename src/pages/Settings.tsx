import { useState } from "react";
import { ExplainCard, SectionHeader } from "@/components/kk/Primitives";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Lock, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

export default function Settings() {
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
  const [mode, setMode] = useState("mock");
  const [refresh, setRefresh] = useState(15);
  const [defaultNiche, setDefaultNiche] = useState("crypto");
  const [maxWallets, setMaxWallets] = useState(50);
  const [minScore, setMinScore] = useState(70);
  const [consensus, setConsensus] = useState(3);
  const [theme, setTheme] = useState("dark");

  return (
    <div className="space-y-5">
      <ExplainCard title="Settings">
        Local configuration only. Paper mode is <strong>locked ON</strong>. KopyKat will never ask for a private key,
        seed phrase, or wallet-connect signature.
      </ExplainCard>

      <div className="panel flex items-center gap-3 border-warning/50 p-3">
        <Lock className="h-5 w-5 text-warning" />
        <div className="text-sm">
          <span className="mono text-warning">PAPER MODE LOCKED.</span>{" "}
          <span className="text-muted-foreground">Cannot be disabled from the UI.</span>
        </div>
        <ShieldAlert className="ml-auto h-5 w-5 text-muted-foreground" />
      </div>

      <SectionHeader title="Backend (mock)" />
      <div className="panel grid gap-4 p-4 md:grid-cols-2">
        <div className="space-y-1.5">
          <Label>Backend URL</Label>
          <Input value={backendUrl} onChange={(e) => setBackendUrl(e.target.value)} className="mono" />
          <p className="text-xs text-muted-foreground">Reserved for a future local backend. Not called in this build.</p>
        </div>
        <div className="space-y-1.5">
          <Label>Backend mode</Label>
          <Select value={mode} onValueChange={setMode}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="mock">Mock</SelectItem>
              <SelectItem value="local">Local</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">Mock uses in-memory fake data. Local is reserved.</p>
        </div>
        <div className="flex items-center justify-between rounded border border-border bg-muted/30 p-3">
          <div>
            <Label>Paper mode</Label>
            <p className="text-xs text-muted-foreground">Locked ON. No real orders permitted.</p>
          </div>
          <Switch checked disabled />
        </div>
        <div className="space-y-1.5">
          <Label>Refresh interval (seconds)</Label>
          <Input type="number" value={refresh} onChange={(e) => setRefresh(Number(e.target.value))} className="mono" />
        </div>
      </div>

      <SectionHeader title="Research defaults" />
      <div className="panel grid gap-4 p-4 md:grid-cols-2">
        <div className="space-y-1.5">
          <Label>Selected niche default</Label>
          <Select value={defaultNiche} onValueChange={setDefaultNiche}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="crypto">Crypto</SelectItem>
              <SelectItem value="sports">Sports</SelectItem>
              <SelectItem value="macro">Macro</SelectItem>
              <SelectItem value="tech">Tech</SelectItem>
              <SelectItem value="global">Global</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Max wallets per niche</Label>
          <Input type="number" value={maxWallets} onChange={(e) => setMaxWallets(Number(e.target.value))} className="mono" />
        </div>
        <div className="space-y-1.5">
          <Label>Minimum wallet score</Label>
          <Input type="number" value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} className="mono" />
        </div>
        <div className="space-y-1.5">
          <Label>Consensus threshold (wallets)</Label>
          <Input type="number" value={consensus} onChange={(e) => setConsensus(Number(e.target.value))} className="mono" />
        </div>
        <div className="space-y-1.5">
          <Label>Theme</Label>
          <Select value={theme} onValueChange={setTheme}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="dark">Dark (terminal)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex justify-end">
        <Button onClick={() => toast.success("Settings saved locally (mock)")}>Save (mock)</Button>
      </div>
    </div>
  );
}
