import { Fragment, useState } from "react";
import { Task } from "@/lib/api";
import { RiskBadge } from "./shared";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export function TaskTable({ tasks }: { tasks: Task[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (tasks.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 text-center text-sm text-muted-foreground">
        No tasks match your filters.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-muted-foreground">
            <tr className="text-left">
              <th className="px-4 py-2.5 font-medium text-xs uppercase tracking-wide w-8"></th>
              <th className="px-4 py-2.5 font-medium text-xs uppercase tracking-wide">Key</th>
              <th className="px-4 py-2.5 font-medium text-xs uppercase tracking-wide">Summary</th>
              <th className="px-4 py-2.5 font-medium text-xs uppercase tracking-wide">Status</th>
              <th className="px-4 py-2.5 font-medium text-xs uppercase tracking-wide">Assignee</th>
              <th className="px-4 py-2.5 font-medium text-xs uppercase tracking-wide">Risk</th>
              <th className="px-4 py-2.5 font-medium text-xs uppercase tracking-wide">Sprint</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => {
              const open = expanded === t.key;
              return (
                <Fragment key={t.key}>
                  <tr
                    className="border-t border-border hover:bg-accent/40 cursor-pointer"
                    onClick={() => setExpanded(open ? null : t.key)}
                  >
                    <td className="px-4 py-2.5">
                      <ChevronRight
                        className={cn(
                          "h-3.5 w-3.5 text-muted-foreground transition-transform",
                          open && "rotate-90"
                        )}
                      />
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs">{t.key}</td>
                    <td className="px-4 py-2.5">{t.summary}</td>
                    <td className="px-4 py-2.5">
                      <span className="text-xs text-muted-foreground">{t.status}</span>
                    </td>
                    <td className="px-4 py-2.5">{t.assignee}</td>
                    <td className="px-4 py-2.5"><RiskBadge score={t.risk_score} /></td>
                    <td className="px-4 py-2.5 text-muted-foreground text-xs">{t.sprint_name}</td>
                  </tr>
                  {open && (
                    <tr className="bg-muted/30 border-t border-border">
                      <td></td>
                      <td colSpan={6} className="px-4 py-3 text-xs text-muted-foreground">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div>
                            <div className="font-medium text-foreground mb-1">Status</div>
                            {t.status}
                          </div>
                          <div>
                            <div className="font-medium text-foreground mb-1">Assignee</div>
                            {t.assignee}
                          </div>
                          <div>
                            <div className="font-medium text-foreground mb-1">Sprint</div>
                            {t.sprint_name}
                          </div>
                          {t.brd_reasoning && (
                            <div className="md:col-span-3">
                              <div className="font-medium text-foreground mb-1">BRD reasoning</div>
                              {t.brd_reasoning}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}