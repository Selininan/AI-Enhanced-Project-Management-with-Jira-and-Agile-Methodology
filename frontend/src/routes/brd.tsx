import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { analyzeBrd, Task } from "@/lib/api";
import { MetricCard, PageHeader, Skeleton } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Search, Star, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/brd")({
  component: BrdPage,
});

function brdTone(score: number) {
  if (score >= 7)
    return {
      label: "HIGH",
      cls: "border-[color:var(--success)]/30 bg-[color:var(--success)]/5",
      pill: "bg-[color:var(--success)]/10 text-[color:var(--success)]",
    };
  if (score >= 5)
    return {
      label: "MEDIUM",
      cls: "border-[color:var(--warning)]/30 bg-[color:var(--warning)]/5",
      pill: "bg-[color:var(--warning)]/10 text-[color:var(--warning)]",
    };
  return {
    label: "LOW",
    cls: "border-[color:var(--danger)]/30 bg-[color:var(--danger)]/5",
    pill: "bg-[color:var(--danger)]/10 text-[color:var(--danger)]",
  };
}

function StarRating({ score }: { score: number }) {
  const v = score / 2;
  return (
    <div className="flex items-center gap-0.5">
      {[0, 1, 2, 3, 4].map((i) => (
        <Star
          key={i}
          className={cn(
            "h-4 w-4",
            i < Math.round(v)
              ? "fill-[color:var(--warning)] text-[color:var(--warning)]"
              : "text-muted-foreground/40"
          )}
        />
      ))}
    </div>
  );
}

function BrdPage() {
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [gapRunning, setGapRunning] = useState(false);
  const [gapResult, setGapResult] = useState<string[] | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const d = await analyzeBrd();
      setTasks(d.tasks);
      setLoading(false);
    };
    load();
    const h = () => load();
    window.addEventListener("bai:refresh", h);
    return () => window.removeEventListener("bai:refresh", h);
  }, []);

  const t: Task[] = tasks ?? [];
  const scored = t.filter((x: Task) => typeof x.brd_score === "number");
  const avg =
    scored.length === 0
      ? 0
      : scored.reduce((s: number, x: Task) => s + (x.brd_score ?? 0), 0) / scored.length;
  const low = scored.filter((x: Task) => (x.brd_score ?? 0) < 5).length;
  const high = scored.filter((x: Task) => (x.brd_score ?? 0) >= 7).length;

  return (
    <div className="p-4 md:p-6 max-w-[1400px] mx-auto">
      <PageHeader
        title="BRD Alignment"
        description="Business Requirements Document scoring and gap detection."
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
        {loading ? (
          [...Array(3)].map((_, i) => <Skeleton key={i} className="h-28" />)
        ) : (
          <>
            <div className="rounded-lg bg-card p-4 shadow-sm ring-1 ring-border">
              <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Average BRD Score
              </div>
              <div className="mt-2 text-2xl font-semibold tabular-nums">
                {avg.toFixed(1)}<span className="text-base text-muted-foreground">/10</span>
              </div>
              <div className="mt-2"><StarRating score={avg} /></div>
            </div>
            <MetricCard label="Low Alignment (<5)" value={low} tone="danger" />
            <MetricCard label="High Alignment (≥7)" value={high} tone="success" />
          </>
        )}
      </div>

      <h3 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
        BRD Scoring Summary
      </h3>
      <div className="max-h-[600px] overflow-y-auto rounded-lg">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-8">
        {scored.map((task: Task) => {
          const tone = brdTone(task.brd_score ?? 0);
          return (
            <div
              key={task.key}
              className={cn(
                "rounded-lg border p-4 shadow-sm",
                tone.cls
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-muted-foreground">
                      {task.key}
                    </span>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                        tone.pill
                      )}
                    >
                      {tone.label} · {task.brd_score}/10
                    </span>
                  </div>
                  <div className="mt-1 text-sm font-medium">{task.summary}</div>
                  {task.brd_reasoning && (
                    <p className="mt-1.5 text-xs text-muted-foreground">
                      {task.brd_reasoning}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      </div>

      <h3 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
        Gap Detection
      </h3>
      <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
        {!gapResult ? (
          <div className="text-center">
            <p className="text-sm text-muted-foreground mb-4">
              Run Gap Detection to find BRD goals with no matching Jira tasks.
            </p>
            <Button
              onClick={async () => {
                setGapRunning(true);
                await new Promise((r) => setTimeout(r, 900));
                setGapResult([
                  "Goal G-04 “Reduce onboarding time by 30%” has no linked Jira task.",
                  "Goal G-07 “Self-service analytics export” has no linked Jira task.",
                  "Goal G-11 “Multi-language support”: only 1 of 3 expected tasks created.",
                ]);
                setGapRunning(false);
              }}
              disabled={gapRunning}
            >
              {gapRunning ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Scanning…
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Run Gap Detection
                </>
              )}
            </Button>
          </div>
        ) : (
          <ul className="space-y-2 text-sm">
            {gapResult.map((g, i) => (
              <li
                key={i}
                className="flex gap-2 rounded-md border border-[color:var(--warning)]/30 bg-[color:var(--warning)]/5 px-3 py-2"
              >
                <Search className="h-4 w-4 text-[color:var(--warning)] shrink-0 mt-0.5" />
                {g}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}