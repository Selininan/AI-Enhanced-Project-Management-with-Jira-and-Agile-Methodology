import { cn } from "@/lib/utils";
import { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
        {description && (
          <p className="text-sm text-muted-foreground mt-1">{description}</p>
        )}
      </div>
      {children}
    </div>
  );
}

export function RiskBadge({ score }: { score: number }) {
  const tone =
    score >= 2.5
      ? "bg-[color:var(--danger)]/10 text-[color:var(--danger)] ring-[color:var(--danger)]/20"
      : score >= 1.5
        ? "bg-[color:var(--warning)]/10 text-[color:var(--warning)] ring-[color:var(--warning)]/20"
        : "bg-[color:var(--success)]/10 text-[color:var(--success)] ring-[color:var(--success)]/20";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset tabular-nums",
        tone
      )}
    >
      {score.toFixed(2)}
    </span>
  );
}

export function StatusBadge({
  status,
}: {
  status: "LOW RISK" | "MEDIUM RISK" | "HIGH RISK" | string;
}) {
  const tone =
    status === "HIGH RISK"
      ? "bg-[color:var(--danger)]/10 text-[color:var(--danger)] ring-[color:var(--danger)]/20"
      : status === "MEDIUM RISK"
        ? "bg-[color:var(--warning)]/10 text-[color:var(--warning)] ring-[color:var(--warning)]/20"
        : status === "LOW RISK"
          ? "bg-[color:var(--success)]/10 text-[color:var(--success)] ring-[color:var(--success)]/20"
          : "bg-muted text-muted-foreground ring-border";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset",
        tone
      )}
    >
      {status}
    </span>
  );
}

export function MetricCard({
  label,
  value,
  icon,
  hint,
  tone,
}: {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "warning" | "danger" | "success";
}) {
  const ring =
    tone === "danger"
      ? "ring-[color:var(--danger)]/15"
      : tone === "warning"
        ? "ring-[color:var(--warning)]/20"
        : tone === "success"
          ? "ring-[color:var(--success)]/20"
          : "ring-border";
  return (
    <div
      className={cn(
        "rounded-lg bg-card p-4 shadow-sm ring-1",
        ring
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          {label}
        </span>
        {icon}
      </div>
      <div className="mt-2 text-2xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-4 rounded-md border border-[color:var(--danger)]/30 bg-[color:var(--danger)]/5 px-4 py-3 text-sm text-[color:var(--danger)]">
      {message}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-muted",
        className
      )}
    />
  );
}

export function CircularProgress({
  value,
  size = 96,
  stroke = 8,
  label,
}: {
  value: number;
  size?: number;
  stroke?: number;
  label?: string;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, value));
  const offset = c - (clamped / 100) * c;
  const tone =
    clamped >= 90
      ? "var(--danger)"
      : clamped >= 75
        ? "var(--warning)"
        : "var(--primary)";
  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="var(--border)"
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={tone}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 600ms ease" }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <div className="text-lg font-semibold tabular-nums">
            {Math.round(clamped)}%
          </div>
          {label && (
            <div className="text-[10px] text-muted-foreground">{label}</div>
          )}
        </div>
      </div>
    </div>
  );
}

export function TypingDots() {
  return (
    <div className="inline-flex items-center gap-1">
      <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce" />
    </div>
  );
}