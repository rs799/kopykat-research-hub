import { Outlet, useLocation } from "react-router-dom";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { ModeBadgeRow } from "@/components/ModeBadges";

const titles: Record<string, { title: string; sub: string }> = {
  "/": { title: "Overview", sub: "System snapshot" },
  "/niches": { title: "Niche Scanner", sub: "Coverage & warnings" },
  "/discovery": { title: "Wallet Discovery", sub: "Public wallets surfaced" },
  "/rankings": { title: "Niche Wallet Rankings", sub: "Top wallets per niche" },
  "/alerts": { title: "Consensus Alerts", sub: "Aligned wallet activity" },
  "/paper": { title: "Paper Simulation", sub: "Simulated research only" },
  "/backtests": { title: "Backtests", sub: "Historical mock evaluation" },
  "/wallets": { title: "Wallet Database", sub: "Surfaced public wallets" },
  "/health": { title: "Data Health", sub: "Parser & ingestion status" },
  "/settings": { title: "Settings", sub: "Local mock configuration" },
};

function StatusStrip() {
  return (
    <div className="flex h-6 items-center justify-between border-b border-border bg-black/60 px-3">
      <ModeBadgeRow />
      <div className="hidden items-center gap-3 md:flex">
        <span className="mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
          KOPYKAT · v0.1.0-mock
        </span>
      </div>
    </div>
  );
}

function TopBar() {
  const { pathname } = useLocation();
  const meta =
    titles[pathname] ??
    (pathname.startsWith("/alerts/")
      ? { title: "Alert Detail", sub: "Consensus alert breakdown" }
      : { title: "KopyKat", sub: "" });

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background">
      <StatusStrip />
      <div className="flex h-9 items-center gap-3 px-3">
        <SidebarTrigger className="text-muted-foreground hover:text-foreground" />
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2">
            <h1 className="mono truncate text-[12px] font-semibold uppercase tracking-[0.18em]">
              {meta.title}
            </h1>
            <span className="mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
              /kopykat{pathname === "/" ? "" : pathname}
            </span>
          </div>
        </div>
        <div className="mono hidden items-center gap-3 text-[10px] uppercase tracking-[0.16em] text-muted-foreground md:flex">
          <span>backend <span className="text-destructive">MOCK</span></span>
          <span>mode <span className="text-warning">PAPER</span></span>
          <span>region <span className="text-foreground">LOCAL</span></span>
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
          <main className="flex-1 px-3 py-3">
            <div className="mx-auto max-w-[1600px] space-y-3">
              <Outlet />
            </div>
          </main>
          <footer className="border-t border-border px-3 py-1.5">
            <div className="mx-auto flex max-w-[1600px] items-center justify-between text-[10px] text-muted-foreground">
              <div className="mono uppercase tracking-[0.16em]">
                KOPYKAT · Local Research Terminal · Frontend-Only
              </div>
              <div className="mono uppercase tracking-[0.16em]">
                No Wallet Connect · No Private Keys · No Real Orders
              </div>
            </div>
          </footer>
        </div>
      </div>
    </SidebarProvider>
  );
}
