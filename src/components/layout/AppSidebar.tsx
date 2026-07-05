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
    <SidebarGroup>
      {!collapsed && (
        <SidebarGroupLabel className="mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
          {label}
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
                      "group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                      active
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                    )}
                  >
                    <item.icon
                      className={cn(
                        "h-4 w-4 shrink-0",
                        active ? "text-accent" : "text-muted-foreground group-hover:text-accent",
                      )}
                    />
                    {!collapsed && <span className="truncate">{item.title}</span>}
                    {active && !collapsed && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-accent" />}
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
        <div className={cn("flex items-center gap-2 px-3 pt-4 pb-2", collapsed && "justify-center px-0")}>
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent/15 text-accent ring-1 ring-accent/40">
            <Activity className="h-4 w-4" />
          </div>
          {!collapsed && (
            <div className="leading-tight">
              <div className="mono text-sm font-bold tracking-widest text-foreground">KOPYKAT</div>
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
          <div className="mt-auto px-3 pb-4">
            <div className="panel p-3">
              <div className="mono text-[10px] uppercase tracking-[0.18em] text-warning">Paper Mode</div>
              <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                No wallet connect. No private keys. No real orders. Mock data only.
              </p>
            </div>
          </div>
        )}
      </SidebarContent>
    </Sidebar>
  );
}
