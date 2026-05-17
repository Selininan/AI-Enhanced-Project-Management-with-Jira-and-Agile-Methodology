// frontend/src/routes/compare.tsx
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { compareProjects, ProjectSummary } from "@/lib/api";
import { useProject } from "@/context/ProjectContext";
import { PageHeader, Skeleton } from "@/components/shared";
import { cn } from "@/lib/utils";
import {
  AlertOctagon, CheckCircle2, AlertTriangle,
  TrendingUp, Users, Clock, Zap,
} from "lucide-react";

export const Route = createFileRoute("/compare")({
  component: ComparePage,
});

function statusColor(status: string) {
  if (status === "HIGH RISK")   return "text-[color:var(--danger)]  bg-[color:var(--danger)]/10  border-[color:var(--danger)]/30";
  if (status === "MEDIUM RISK") return "text-[color:var(--warning)] bg-[color:var(--warning)]/10 border-[color:var(--warning)]/30";
  return "text-[color:var(--success)] bg-[color:var(--success)]/10 border-[color:var(--success)]/30";
}

function StatusIcon({ status }: { status: string }) {
  if (status === "HIGH RISK")   return <AlertOctagon className="h-4 w-4" />;
  if (status === "MEDIUM RISK") return <AlertTriangle className="h-4 w-4" />;
  return <CheckCircle2 className="h-4 w-4" />;
}

function MiniBar({ value, max, color }: { value: number; max: number; color: string }) {
  return (
    <div className="h-1.5 rounded-full bg-muted overflow-hidden w-full">
      <div
        className={cn("h-full rounded-full transition-all", color)}
        style={{ width: `${Math.min((value / max) * 100, 100)}%` }}
      />
    </div>
  );
}

function ComparePage() {
  const { projects } = useProject();
  const [data, setData]       = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");

  useEffect(() => {
    const load = async () => {
      if (projects.length === 0) return;
      setLoading(true);
      setError("");
      try {
        const keys = projects.map((p) => p.key);
        const result = await compareProjects(keys);
        setData(result);
      } catch {
        setError("Karşılaştırma verisi alınamadı. Backend çalışıyor mu?");
      }
      setLoading(false);
    };
    load();
    const h = () => load();
    window.addEventListener("bai:refresh", h);
    return () => window.removeEventListener("bai:refresh", h);
  }, [projects]);

  const maxTasks   = Math.max(...data.map((d) => d.total_tasks), 1);
  const maxRisk    = Math.max(...data.map((d) => d.average_risk), 1);
  const maxUtil    = Math.max(...data.map((d) => d.utilization_pct), 1);

  return (
    <div className="p-4 md:p-6 max-w-[1400px] mx-auto">
      <PageHeader
        title="Compare Projects"
        description="Side-by-side AI analysis of all Jira projects — sprint health, capacity and risk."
      />

      {error && (
        <div className="mb-4 rounded-md border border-[color:var(--danger)]/30 bg-[color:var(--danger)]/5 px-4 py-3 text-sm text-[color:var(--danger)]">
          {error}
        </div>
      )}

      {/* ── Kart Grid ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-8">
        {loading
          ? [...Array(3)].map((_, i) => <Skeleton key={i} className="h-64" />)
          : data.map((p) => (
              <div
                key={p.project_key}
                className={cn(
                  "rounded-xl border bg-card shadow-sm p-5 space-y-4",
                  p.error ? "opacity-60" : ""
                )}
              >
                {/* Başlık */}
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-lg font-bold tracking-tight">{p.project_key}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {p.total_tasks} tasks total
                    </div>
                  </div>
                  {!p.error && (
                    <span className={cn("flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold", statusColor(p.sprint_status))}>
                      <StatusIcon status={p.sprint_status} />
                      {p.sprint_status}
                    </span>
                  )}
                </div>

                {p.error ? (
                  <div className="text-xs text-muted-foreground italic">{p.error}</div>
                ) : (
                  <>
                    {/* Metrikler */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-lg bg-muted/40 px-3 py-2">
                        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mb-1">
                          <Zap className="h-3 w-3" />
                          Avg Risk
                        </div>
                        <div className="text-xl font-semibold tabular-nums">
                          {p.average_risk.toFixed(2)}
                        </div>
                        <MiniBar value={p.average_risk} max={maxRisk} color="bg-[color:var(--danger)]" />
                      </div>
                      <div className="rounded-lg bg-muted/40 px-3 py-2">
                        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mb-1">
                          <Clock className="h-3 w-3" />
                          Utilization
                        </div>
                        <div className="text-xl font-semibold tabular-nums">
                          {p.utilization_pct.toFixed(0)}%
                        </div>
                        <MiniBar
                          value={p.utilization_pct}
                          max={100}
                          color={p.utilization_pct >= 90 ? "bg-[color:var(--danger)]" : p.utilization_pct >= 75 ? "bg-[color:var(--warning)]" : "bg-primary"}
                        />
                      </div>
                    </div>

                    {/* Alt satır */}
                    <div className="flex items-center justify-between text-xs text-muted-foreground border-t border-border pt-3">
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2 className="h-3.5 w-3.5 text-[color:var(--success)]" />
                        {p.completed} completed
                      </div>
                      <div className="flex items-center gap-1.5">
                        <AlertTriangle className="h-3.5 w-3.5 text-[color:var(--warning)]" />
                        {p.delayed} delayed
                      </div>
                      <div className="flex items-center gap-1.5">
                        <AlertOctagon className="h-3.5 w-3.5 text-[color:var(--danger)]" />
                        {p.high_risk} high risk
                      </div>
                    </div>

                    {/* Kapasite bar */}
                    <div>
                      <div className="flex justify-between text-[11px] text-muted-foreground mb-1.5">
                        <span className="flex items-center gap-1"><Users className="h-3 w-3" /> Capacity</span>
                        <span>{p.total_effort}h / {p.team_capacity}h</span>
                      </div>
                      <MiniBar
                        value={p.total_effort}
                        max={p.team_capacity || 1}
                        color={p.total_effort > p.team_capacity ? "bg-[color:var(--danger)]" : "bg-[color:var(--success)]"}
                      />
                    </div>
                  </>
                )}
              </div>
            ))}
      </div>

      {/* ── Tablo Karşılaştırması ── */}
      {!loading && data.filter((d) => !d.error).length > 0 && (
        <>
          <h3 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            Detailed Comparison
          </h3>
          <div className="rounded-lg border border-border bg-card shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide">Project</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide">Tasks</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide">Completed</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide">Delayed</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide">High Risk</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide">Avg Risk</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide">Utilization</th>
                    <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wide">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((p) => (
                    <tr key={p.project_key} className="border-t border-border hover:bg-accent/30 transition-colors">
                      <td className="px-4 py-3 font-semibold">{p.project_key}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{p.error ? "—" : p.total_tasks}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-[color:var(--success)]">{p.error ? "—" : p.completed}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-[color:var(--warning)]">{p.error ? "—" : p.delayed}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-[color:var(--danger)]">{p.error ? "—" : p.high_risk}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{p.error ? "—" : p.average_risk.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{p.error ? "—" : `${p.utilization_pct.toFixed(0)}%`}</td>
                      <td className="px-4 py-3 text-center">
                        {p.error ? (
                          <span className="text-xs text-muted-foreground">No data</span>
                        ) : (
                          <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold", statusColor(p.sprint_status))}>
                            <StatusIcon status={p.sprint_status} />
                            {p.sprint_status}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
