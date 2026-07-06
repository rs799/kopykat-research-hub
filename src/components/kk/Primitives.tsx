import { cn } from "@/lib/utils";

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
    <div className={cn("panel border-l-2 border-l-info px-3 py-2", className)}>
      <div className="mono text-[10px] uppercase tracking-[0.16em] text-info">
        NOTE // {title}
      </div>
      <div className="mt-0.5 text-[12px] leading-snug text-muted-foreground">{children}</div>
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
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
    <div className="panel px-3 py-2">
      <div className="mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </div>
      <div className={cn("mono mt-0.5 text-lg font-semibold leading-tight", toneClass)}>
        {value}
      </div>
      {hint && (
        <div className="mono mt-0.5 text-[10px] uppercase tracking-wider text-muted-foreground/80">
          {hint}
        </div>
      )}
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
    <div className="mb-2 flex items-end justify-between gap-3 border-b border-border pb-1">
      <div>
        <h2 className="mono text-[11px] font-semibold uppercase tracking-[0.2em] text-foreground">
          {title}
        </h2>
        {subtitle && (
          <p className="mono text-[10px] uppercase tracking-wider text-muted-foreground">
            {subtitle}
          </p>
        )}
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
    muted: "text-muted-foreground border-border",
    success: "text-success border-success/40",
    warning: "text-warning border-warning/40",
    danger: "text-destructive border-destructive/40",
    info: "text-info border-info/40",
    accent: "text-accent border-accent/40",
  };
  return (
    <span
      className={cn(
        "mono inline-flex items-center rounded-none border px-1 py-0 text-[10px] font-medium uppercase tracking-wider bg-transparent",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}

export function Addr({ value }: { value: string }) {
  return (
    <span className="mono text-[11px] text-foreground/90" title={value}>
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
