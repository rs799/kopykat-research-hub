import { NavLink, useLocation } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Beaker,
  Database,
  FlaskConical,
  Gauge,
  LayoutDashboard,
  Radar,
  Settings,
  Trophy,
  Users,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";

const research = [
  { title: "Overview", url: "/", icon: LayoutDashboard },
  { title: "Niche Scanner", url: "/niches", icon: Radar },
  { title: "Wallet Discovery", url: "/discovery", icon: Users },
  { title: "Niche Rankings", url: "/rankings", icon: Trophy },
];
const signals = [
  { title: "Consensus Alerts", url: "/alerts", icon: AlertTriangle },
  { title: "Paper Simulation", url: "/paper", icon: FlaskConical },
  { title: "Backtests", url: "/backtests", icon: Beaker },
];
const system = [
  { title: "Wallet Database", url: "/wallets", icon: Database },
  { title: "Data Health", url: "/health", icon: Gauge },
  { title: "Settings", url: "/settings", icon: Settings },
];

function Section({
  label,
  items,
}: {
  label: string;
  items: { title: string; url: string; icon: React.ComponentType<{ className?: string }> }[];
}) {
  const { pathname } = useLocation();
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  return (
    <SidebarGroup className="py-1">
      {!collapsed && (
        <SidebarGroupLabel className="mono px-2 pb-0.5 text-[9px] uppercase tracking-[0.2em] text-muted-foreground/60">
          // {label}
        </SidebarGroupLabel>
      )}
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => {
            const active = pathname === item.url;
            return (
              <SidebarMenuItem key={item.url}>
                <SidebarMenuButton asChild isActive={active}>
                  <NavLink
                    to={item.url}
                    end={item.url === "/"}
                    className={cn(
                      "mono group flex items-center gap-2 rounded-none px-2 py-1 text-[11px] uppercase tracking-[0.1em] transition-colors",
                      active
                        ? "bg-sidebar-accent text-accent border-l-2 border-accent"
                        : "text-sidebar-foreground border-l-2 border-transparent hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
                    )}
                  >
                    <item.icon
                      className={cn(
                        "h-3 w-3 shrink-0",
                        active ? "text-accent" : "text-muted-foreground group-hover:text-accent",
                      )}
                    />
                    {!collapsed && <span className="truncate">{item.title}</span>}
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  return (
    <Sidebar collapsible="icon" className="border-r border-sidebar-border">
      <SidebarContent>
        <div className={cn("flex items-center gap-2 border-b border-sidebar-border px-2 py-2", collapsed && "justify-center px-0")}>
          <div className="flex h-6 w-6 items-center justify-center border border-accent/60 text-accent">
            <Activity className="h-3 w-3" />
          </div>
          {!collapsed && (
            <div className="leading-tight">
              <div className="mono text-[12px] font-bold tracking-[0.22em] text-foreground">KOPYKAT</div>
              <div className="mono text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
                research terminal
              </div>
            </div>
          )}
        </div>
        <Section label="Research" items={research} />
        <Section label="Signals" items={signals} />
        <Section label="System" items={system} />

        {!collapsed && (
          <div className="mt-auto border-t border-sidebar-border px-2 py-2">
            <div className="mono text-[9px] uppercase leading-relaxed tracking-[0.16em] text-muted-foreground">
              <div className="text-warning">// PAPER MODE LOCKED</div>
              <div>no wallet connect</div>
              <div>no private keys</div>
              <div>no real orders</div>
              <div>mock data only</div>
            </div>
          </div>
        )}
      </SidebarContent>
    </Sidebar>
  );
}
