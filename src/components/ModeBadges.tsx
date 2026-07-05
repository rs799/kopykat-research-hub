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
    warn: "border-warning/50 text-warning bg-warning/10",
    info: "border-info/50 text-info bg-info/10",
    danger: "border-destructive/50 text-destructive bg-destructive/10",
    ok: "border-success/50 text-success bg-success/10",
    muted: "border-border text-muted-foreground bg-muted/40",
  };
  return (
    <span
      className={cn(
        "mono inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em]",
        tones[tone],
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse-dot" />
      {children}
    </span>
  );
}

export function ModeBadgeRow() {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <ModeBadge tone="warn">Paper Mode Only</ModeBadge>
      <ModeBadge tone="info">Mock Data</ModeBadge>
      <ModeBadge tone="muted">Local</ModeBadge>
    </div>
  );
}
