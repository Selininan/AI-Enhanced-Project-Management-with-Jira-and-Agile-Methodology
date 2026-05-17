import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AlertTriangle, CircleDot, ListTodo, Lightbulb } from "lucide-react";
import { analyzeSprint, SprintAnalysis } from "@/lib/api";
import { useProject } from "@/context/ProjectContext";
import {
  CircularProgress,
  MetricCard,
  PageHeader,
  Skeleton,
  StatusBadge,
} from "@/components/shared";
import { TaskTable } from "@/components/TaskTable";

export const Route = createFileRoute("/")({
  component: Dashboard,
});

function Dashboard() {
  const { selectedProject } = useProject();
  const [data, setData] = useState<SprintAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setData(null);
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const d = await analyzeSprint(selectedProject);
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

  if (!loading && error) return <div className="p-6 text-destructive">{error}</div>;

  return (
    <div className="p-4 md:p-6 max-w-[1400px] mx-auto">
      <PageHeader
        title="Dashboard"
        description="Overview of your current sprint health and AI recommendations."
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {loading ? (
          [...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)
        ) : (
          <>
            <MetricCard
              label="Total Tasks"
              value={data?.total_tasks ?? 0}
              icon={<ListTodo className="h-4 w-4 text-muted-foreground" />}
            />
            <MetricCard
              label="Sprint Status"
              value={data ? <StatusBadge status={data.sprint_status} /> : "-"}
              hint={data ? `avg risk ${data.average_risk.toFixed(2)}` : ""}
              tone={
                data?.sprint_status === "HIGH RISK"
                  ? "danger"
                  : data?.sprint_status === "MEDIUM RISK"
                    ? "warning"
                    : "success"
              }
            />
            <MetricCard
              label="Delayed Tasks"
              value={data?.delayed_tasks ?? 0}
              icon={<AlertTriangle className="h-4 w-4 text-[color:var(--warning)]" />}
              tone="warning"
            />
            <MetricCard
              label="High Risk Tasks"
              value={data?.high_risk_tasks ?? 0}
              icon={<CircleDot className="h-4 w-4 text-[color:var(--danger)]" />}
              tone="danger"
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-3">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Task list
          </h3>
          {loading ? (
            <Skeleton className="h-80" />
          ) : (
            <div className="max-h-[600px] overflow-y-auto rounded-lg">
              <TaskTable tasks={data?.tasks ?? []} />
            </div>
          )}
        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            🤖 Sprint Optimization
          </h3>
          <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <div className="flex items-center gap-4">
              <CircularProgress value={data?.load_percentage ?? 0} label="loaded" />
              <div>
                <div className="text-sm font-medium">
                  Your sprint is {data?.load_percentage ?? 0}% loaded
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  Based on {data?.total_tasks ?? 0} tasks across active sprints.
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <div className="text-sm font-medium mb-3">AI recommendations</div>
            <ul className="space-y-2.5">
              {(data?.recommendations ?? []).map((r: string, i: number) => (
                <li key={i} className="flex gap-2 text-sm">
                  <Lightbulb className="h-4 w-4 text-[color:var(--warning)] shrink-0 mt-0.5" />
                  <span className="text-foreground">{r}</span>
                </li>
              ))}
            </ul>
          </div>

        </div>
      </div>
    </div>
  );
}
