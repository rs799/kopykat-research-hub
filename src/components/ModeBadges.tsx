import { cn } from "@/lib/utils";

export function ModeBadge({
  tone = "warn",
  children,
  className,
}: {
  tone?: "warn" | "info" | "danger" | "ok" | "muted";
  children: React.ReactNode;
  className?: string;
}) {
  const tones: Record<string, string> = {
    warn: "text-warning",
    info: "text-info",
    danger: "text-destructive",
    ok: "text-success",
    muted: "text-muted-foreground",
  };
  return (
    <span
      className={cn(
        "mono inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.14em]",
        tones[tone],
        className,
      )}
    >
      <span className="h-1.5 w-1.5 bg-current" />
      {children}
    </span>
  );
}

const Sep = () => <span className="mono text-[10px] text-border">|</span>;

export function ModeBadgeRow() {
  const now = new Date();
  const time = now.toLocaleTimeString(undefined, { hour12: false });
  return (
    <div className="flex flex-wrap items-center gap-2">
      <ModeBadge tone="warn">Paper Mode Only</ModeBadge>
      <Sep />
      <ModeBadge tone="info">Mock Data</ModeBadge>
      <Sep />
      <ModeBadge tone="muted">Local</ModeBadge>
      <Sep />
      <ModeBadge tone="danger">Backend: Disconnected</ModeBadge>
      <Sep />
      <span className="mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
        Last Refresh <span className="text-foreground">{time}</span>
      </span>
    </div>
  );
}
