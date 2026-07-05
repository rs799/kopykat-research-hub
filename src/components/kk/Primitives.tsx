import { cn } from "@/lib/utils";
import { Info } from "lucide-react";

export function ExplainCard({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("panel flex gap-3 p-4", className)}>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-info/10 text-info">
        <Info className="h-4 w-4" />
      </div>
      <div className="space-y-1">
        <div className="mono text-[11px] uppercase tracking-[0.16em] text-info">Beginner: {title}</div>
        <div className="text-sm leading-relaxed text-muted-foreground">{children}</div>
      </div>
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
  mono = true,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  tone?: "default" | "success" | "warning" | "danger" | "info";
  mono?: boolean;
}) {
  const toneClass = {
    default: "text-foreground",
    success: "text-success",
    warning: "text-warning",
    danger: "text-destructive",
    info: "text-info",
  }[tone];
  return (
    <div className="panel p-4">
      <div className="mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
      <div className={cn("mt-1.5 text-2xl font-semibold", mono && "mono", toneClass)}>{value}</div>
      {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}

export function SectionHeader({
  title,
  subtitle,
  right,
}: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="mb-3 flex items-end justify-between gap-3">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Pill({
  children,
  tone = "muted",
}: {
  children: React.ReactNode;
  tone?: "muted" | "success" | "warning" | "danger" | "info" | "accent";
}) {
  const tones: Record<string, string> = {
    muted: "border-border bg-muted/40 text-muted-foreground",
    success: "border-success/40 bg-success/10 text-success",
    warning: "border-warning/40 bg-warning/10 text-warning",
    danger: "border-destructive/40 bg-destructive/10 text-destructive",
    info: "border-info/40 bg-info/10 text-info",
    accent: "border-accent/40 bg-accent/10 text-accent",
  };
  return (
    <span
      className={cn(
        "mono inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}

export function Addr({ value }: { value: string }) {
  return (
    <span className="mono text-xs text-foreground/90" title={value}>
      {value.slice(0, 6)}…{value.slice(-4)}
    </span>
  );
}

export function fmtUsd(n: number) {
  const sign = n < 0 ? "-" : "";
  return `${sign}$${Math.abs(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}
export function fmtPct(n: number, digits = 1) {
  return `${(n * 100).toFixed(digits)}%`;
}
