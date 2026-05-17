const STORAGE_KEY = "bai_api_base_url";
const DEFAULT_BASE = "http://localhost:8000";

export function getBaseUrl(): string {
  if (typeof window === "undefined") return DEFAULT_BASE;
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_BASE;
}

export function setBaseUrl(url: string) {
  if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, url);
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${getBaseUrl()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${getBaseUrl()}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

export interface Task {
  key: string;
  summary: string;
  status: string;
  assignee: string;
  risk_score: number;
  sprint_name: string;
  brd_score?: number;
  brd_reasoning?: string;
}

export interface SprintAnalysis {
  sprint_status: "LOW RISK" | "MEDIUM RISK" | "HIGH RISK";
  average_risk: number;
  total_tasks: number;
  delayed_tasks: number;
  high_risk_tasks: number;
  recommendations: string[];
  tasks: Task[];
  load_percentage: number;
}

export interface CapacityReport {
  team_capacity: number;
  total_effort: number;
  utilization: number;
  is_overloaded: boolean;
  bottleneck_report: { level: "ok" | "warning" | "critical"; message: string }[];
  workload: { assignee: string; story_points: number }[];
}

export const analyzeSprint = () =>
  request<SprintAnalysis>("/analyze/sprint");

export const analyzeCapacity = () =>
  request<CapacityReport>("/analyze/capacity");

export const analyzeBrd = () =>
  fetch(`${getBaseUrl()}/analyze/brd-report`)
    .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
    .then((d) => ({ tasks: d.tasks as Task[] }));

export async function supportAsk(question: string): Promise<string> {
  const data = await request<{ answer: string }>("/support/ask", {
    body: JSON.stringify({ question }),
  });
  return data.answer;
}
