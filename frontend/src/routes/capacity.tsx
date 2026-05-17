import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  analyzeCapacity,
  CapacityReport,
} from "@/lib/api";
import { useProject } from "@/context/ProjectContext";
import {
  CircularProgress,
  MetricCard,
  PageHeader,
  Skeleton,
} from "@/components/shared";
import { AlertOctagon, AlertTriangle, CheckCircle2 } from "lucide-react";

export const Route = createFileRoute("/capacity")({
  component: CapacityPage,
});

function CapacityPage() {
  const { selectedProject } = useProject();
  const [data, setData] = useState<CapacityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setData(null);
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const d = await analyzeCapacity(selectedProject);
        if (!cancelled) setData(d);
      } catch {
        if (!cancelled) setError("Could not connect to backend. Is FastAPI running?");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [selectedProject]);

  const maxPts = Math.max(...(data?.workload ?? []).map((w: CapacityReport["workload"][0]) => w.story_points), 1);

  return (
    <div className="p-4 md:p-6 max-w-[1400px] mx-auto">
      <PageHeader
        title="Capacity Report"
        description="Team capacity, workload distribution, and bottlenecks."
      />

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
        {loading ? (
          [...Array(3)].map((_, i) => <Skeleton key={i} className="h-28" />)
        ) : (
          <>
            <MetricCard label="Team Capacity" value={`${data?.team_capacity ?? 0}h`} />
            <MetricCard label="Total Workload" value={`${data?.total_effort ?? 0}h`} />
            <div className="rounded-lg bg-card p-4 shadow-sm ring-1 ring-border flex items-center gap-4">
              <CircularProgress value={data?.utilization ?? 0} label="utilization" size={84} />
              <div>
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Utilization
                </div>
                <div className="text-2xl font-semibold tabular-nums">
                  {(data?.utilization ?? 0).toFixed(1)}%
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {data?.is_overloaded && (
        <div className="mb-6 flex items-start gap-3 rounded-md border border-[color:var(--danger)]/30 bg-[color:var(--danger)]/5 px-4 py-3 text-sm text-[color:var(--danger)]">
          <AlertOctagon className="h-5 w-5 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">Team is overloaded</div>
            <div className="text-xs mt-0.5 opacity-90">
              Workload exceeds available capacity. Consider rebalancing or
              deferring scope.
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h3 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Bottleneck report
          </h3>
          <div className="space-y-2">
            {(data?.bottleneck_report ?? []).map((b: CapacityReport["bottleneck_report"][0], i: number) => {
              const Icon =
                b.level === "critical"
                  ? AlertOctagon
                  : b.level === "warning"
                    ? AlertTriangle
                    : CheckCircle2;
              const color =
                b.level === "critical"
                  ? "text-[color:var(--danger)] border-[color:var(--danger)]/30 bg-[color:var(--danger)]/5"
                  : b.level === "warning"
                    ? "text-[color:var(--warning)] border-[color:var(--warning)]/30 bg-[color:var(--warning)]/5"
                    : "text-[color:var(--success)] border-[color:var(--success)]/30 bg-[color:var(--success)]/5";
              return (
                <div
                  key={i}
                  className={`flex items-start gap-3 rounded-md border px-4 py-3 text-sm ${color}`}
                >
                  <Icon className="h-4 w-4 shrink-0 mt-0.5" />
                  <span className="text-foreground">{b.message}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Workload by assignee
          </h3>
          <div className="rounded-lg border border-border bg-card p-5 shadow-sm space-y-4">
            {(data?.workload ?? []).map((w: CapacityReport["workload"][0]) => (
              <div key={w.assignee}>
                <div className="flex justify-between text-sm mb-1.5">
                  <span className="font-medium">{w.assignee}</span>
                  <span className="text-muted-foreground tabular-nums">
                    {w.story_points} pts
                  </span>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${(w.story_points / maxPts) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}