import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { analyzeSprint, SprintAnalysis, Task } from "@/lib/api";
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
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/sprint-analysis")({
  component: SprintAnalysisPage,
});

const STATE_ORDER: Record<string, number> = { active: 0, future: 1, closed: 2 };

function sprintStyle(state: string) {
  if (state === "active")
    return {
      border: "border-l-4 border-l-[color:var(--success)]",
      badge: "bg-[color:var(--success)]/10 text-[color:var(--success)]",
      label: "Active",
    };
  if (state === "future")
    return {
      border: "border-l-4 border-l-blue-500",
      badge: "bg-blue-500/10 text-blue-500",
      label: "Future",
    };
  if (state === "closed")
    return {
      border: "border-l-4 border-l-muted-foreground/40",
      badge: "bg-muted text-muted-foreground",
      label: "Closed",
    };
  return {
    border: "border-l-4 border-l-border",
    badge: "bg-muted text-muted-foreground",
    label: "No Sprint",
  };
}

interface SprintGroup {
  name: string;
  state: string;
  tasks: Task[];
}

function SprintCard({
  group,
  highlighted,
}: {
  group: SprintGroup;
  highlighted: boolean;
}) {
  const [open, setOpen] = useState(group.state === "active");
  const style = sprintStyle(group.state);

  const total     = group.tasks.length;
  const delayed   = group.tasks.filter((t) => t.risk_score >= 2).length;
  const highRisk  = group.tasks.filter((t) => t.risk_score >= 2.5).length;
  const avgRisk   = total
    ? (group.tasks.reduce((s, t) => s + t.risk_score, 0) / total).toFixed(2)
    : "0.00";

  return (
    <div
      className={cn(
        "rounded-lg border bg-card shadow-sm transition-all",
        style.border,
        highlighted && "ring-2 ring-primary ring-offset-2"
      )}
    >
      <button
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-3 min-w-0">
          {open ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
          <span className="font-medium text-sm truncate">
            {group.name}
          </span>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-semibold shrink-0",
              style.badge
            )}
          >
            {style.label}
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground shrink-0 ml-4">
          <span>{total} tasks</span>
          <span className="text-[color:var(--warning)]">{delayed} delayed</span>
          <span className="text-[color:var(--danger)]">{highRisk} high risk</span>
          <span>avg risk {avgRisk}</span>
        </div>
      </button>

      {open && (
        <div className="border-t border-border px-4 pb-4 pt-3">
          <TaskTable tasks={group.tasks} />
        </div>
      )}
    </div>
  );
}

function SprintAnalysisPage() {
  const { selectedProject } = useProject();
  const [data, setData] = useState<SprintAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sprint, setSprint] = useState("all");
  const [status, setStatus] = useState("all");
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({});

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

  const sprintGroups = useMemo<SprintGroup[]>(() => {
    const map: Record<string, SprintGroup> = {};
    for (const t of tasks) {
      const key = t.sprint_name || "No Sprint Assigned";
      if (!map[key]) {
        map[key] = { name: key, state: t.sprint_state ?? "", tasks: [] };
      }
      map[key].tasks.push(t);
    }
    return Object.values(map).sort((a, b) => {
      const oa = STATE_ORDER[a.state] ?? 3;
      const ob = STATE_ORDER[b.state] ?? 3;
      return oa !== ob ? oa - ob : a.name.localeCompare(b.name);
    });
  }, [tasks]);

  useEffect(() => {
    if (sprint !== "all" && cardRefs.current[sprint]) {
      cardRefs.current[sprint]?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [sprint]);

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

      <h3 className="mt-4 mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
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

      <h3 className="mt-8 mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
        Sprint Breakdown
      </h3>
      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16" />)}
        </div>
      ) : (
        <div className="space-y-3">
          {sprintGroups.map((group) => (
            <div
              key={group.name}
              ref={(el) => { cardRefs.current[group.name] = el; }}
            >
              <SprintCard
                group={group}
                highlighted={sprint === group.name}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
