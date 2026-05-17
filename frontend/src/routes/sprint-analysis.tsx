import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import {
  analyzeSprint,
  SprintAnalysis,
} from "@/lib/api";
import { useProject } from "@/context/ProjectContext";
import {
  MetricCard,
  PageHeader,
  Skeleton,
  StatusBadge,
} from "@/components/shared";
import { TaskTable } from "@/components/TaskTable";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export const Route = createFileRoute("/sprint-analysis")({
  component: SprintAnalysisPage,
});

function SprintAnalysisPage() {
  const { selectedProject } = useProject();
  const [data, setData] = useState<SprintAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sprint, setSprint] = useState("all");
  const [status, setStatus] = useState("all");

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

  const tasks = data?.tasks ?? [];

  const sprints = useMemo(
    () => Array.from(new Set(tasks.map((t) => t.sprint_name))).filter(Boolean),
    [tasks]
  );
  const statuses = useMemo(
    () => Array.from(new Set(tasks.map((t) => t.status))).filter(Boolean),
    [tasks]
  );
  const filtered = tasks.filter(
    (t) =>
      (sprint === "all" || t.sprint_name === sprint) &&
      (status === "all" || t.status === status)
  );

  const chartData = filtered.map((t) => ({
    key: t.key,
    score: t.risk_score,
    fill:
      t.risk_score >= 2.5
        ? "var(--danger)"
        : t.risk_score >= 1.5
          ? "var(--warning)"
          : "var(--success)",
  }));

  return (
    <div className="p-4 md:p-6 max-w-[1400px] mx-auto">
      <PageHeader
        title="Sprint Analysis"
        description="Full sprint health report with filters and risk distribution."
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {loading ? (
          [...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)
        ) : (
          <>
            <MetricCard label="Sprint Status" value={data ? <StatusBadge status={data.sprint_status} /> : "-"} />
            <MetricCard label="Avg Risk" value={data ? data.average_risk.toFixed(2) : "-"} />
            <MetricCard label="Delayed" value={data?.delayed_tasks ?? 0} tone="warning" />
            <MetricCard label="High Risk" value={data?.high_risk_tasks ?? 0} tone="danger" />
            {error && <p className="col-span-4 text-sm text-destructive">{error}</p>}
          </>
        )}
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        <Select value={sprint} onValueChange={setSprint}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Sprint" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All sprints</SelectItem>
            {sprints.map((s) => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {statuses.map((s) => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <Skeleton className="h-80" />
      ) : (
        <div className="max-h-[600px] overflow-y-auto rounded-lg">
          <TaskTable tasks={filtered} />
        </div>
      )}

      <h3 className="mt-8 mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
        Risk score distribution
      </h3>
      <div className="rounded-lg border border-border bg-card p-4 shadow-sm h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="key" stroke="var(--muted-foreground)" fontSize={11} />
            <YAxis stroke="var(--muted-foreground)" fontSize={11} />
            <Tooltip
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Bar dataKey="score" radius={[6, 6, 0, 0]}>
              {chartData.map((e, i) => (
                <Cell key={i} fill={e.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}