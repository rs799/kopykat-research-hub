import { Outlet, useLocation } from "react-router-dom";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { ModeBadgeRow } from "@/components/ModeBadges";
import { Cpu, ShieldAlert } from "lucide-react";

const titles: Record<string, { title: string; sub: string }> = {
  "/": { title: "Overview", sub: "System snapshot — research pipeline health at a glance." },
  "/niches": { title: "Niche Scanner", sub: "Inventory of niches, coverage, and warnings." },
  "/discovery": { title: "Wallet Discovery", sub: "Public wallets surfaced from on-chain activity (mock)." },
  "/rankings": { title: "Niche Wallet Rankings", sub: "Top public wallets per niche, scored on mock history." },
  "/alerts": { title: "Consensus Alerts", sub: "When several top wallets appear to take the same side." },
  "/paper": { title: "Paper Simulation", sub: "Simulated research only — no real orders." },
  "/backtests": { title: "Backtests", sub: "Mock historical evaluation of strategies and niches." },
  "/wallets": { title: "Wallet Database", sub: "Every public wallet KopyKat has surfaced (mock)." },
  "/health": { title: "Data Health", sub: "Parser warnings, ingestion status, lifecycle checks." },
  "/settings": { title: "Settings", sub: "Local, mock-only configuration. Paper mode is locked ON." },
};

function TopBar() {
  const { pathname } = useLocation();
  const meta =
    titles[pathname] ??
    (pathname.startsWith("/alerts/") ? { title: "Alert Detail", sub: "Full breakdown of a consensus alert." } : {
      title: "KopyKat",
      sub: "",
    });
  const now = new Date();
  const time = now.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/85 backdrop-blur">
      <div className="flex h-14 items-center gap-3 px-4">
        <SidebarTrigger className="text-muted-foreground hover:text-foreground" />
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2">
            <h1 className="truncate text-sm font-semibold tracking-tight">{meta.title}</h1>
            <span className="mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              /kopykat{pathname === "/" ? "" : pathname}
            </span>
          </div>
          <p className="hidden truncate text-xs text-muted-foreground md:block">{meta.sub}</p>
        </div>

        <div className="hidden items-center gap-2 md:flex">
          <ModeBadgeRow />
        </div>

        <div className="hidden items-center gap-3 border-l border-border pl-3 md:flex">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Cpu className="h-3.5 w-3.5 text-accent" />
            <span className="mono">backend</span>
            <span className="mono text-foreground">MOCK</span>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <ShieldAlert className="h-3.5 w-3.5 text-warning" />
            <span className="mono">mode</span>
            <span className="mono text-warning">PAPER</span>
          </div>
          <span className="mono text-[11px] text-muted-foreground">{time}</span>
        </div>
      </div>
    </header>
  );
}

export default function AppLayout() {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background">
        <AppSidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <main className="flex-1 px-4 py-5 md:px-6">
            <div className="mx-auto max-w-[1500px] space-y-5">
              <Outlet />
            </div>
          </main>
          <footer className="border-t border-border px-4 py-3">
            <div className="mx-auto flex max-w-[1500px] items-center justify-between text-[11px] text-muted-foreground">
              <div className="mono uppercase tracking-[0.18em]">
                KopyKat · Local Research Terminal · v0.1.0-mock
              </div>
              <div className="mono uppercase tracking-[0.18em]">
                Frontend only · No wallet connect · No real orders
              </div>
            </div>
          </footer>
        </div>
      </div>
    </SidebarProvider>
  );
}
