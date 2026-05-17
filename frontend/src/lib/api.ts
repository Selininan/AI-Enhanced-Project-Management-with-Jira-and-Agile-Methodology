// frontend/src/lib/api.ts
// Multi-project desteği eklenmiş versiyon

const STORAGE_KEY = "bai_api_base_url";
const DEFAULT_BASE = "http://localhost:8000";

export function getBaseUrl(): string {
  if (typeof window === "undefined") return DEFAULT_BASE;
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_BASE;
}

export function setBaseUrl(url: string) {
  if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, url);
}

// ── Temel istek fonksiyonu ──────────────────────────────────────────────────

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${getBaseUrl()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${getBaseUrl()}${path}`, { method: "GET" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Health ──────────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${getBaseUrl()}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

// ── Proje listesi (YENİ) ────────────────────────────────────────────────────

export interface JiraProject {
  key:  string;
  name: string;
}

export async function listProjects(): Promise<JiraProject[]> {
  try {
    const data = await get<{ projects: JiraProject[] }>("/projects");
    return data.projects;
  } catch {
    // Backend'e ulaşamazsa default liste döner
    return [{ key: "BAI", name: "Beko AI Sprint Management" }];
  }
}

// ── Tipler ──────────────────────────────────────────────────────────────────

export interface Task {
  key:          string;
  summary:      string;
  status:       string;
  assignee:     string;
  risk_score:   number;
  sprint_name:  string;
  brd_score?:   number;
  brd_reasoning?: string;
}

export interface SprintAnalysis {
  project_key:     string;
  sprint_status:   "LOW RISK" | "MEDIUM RISK" | "HIGH RISK";
  average_risk:    number;
  total_tasks:     number;
  delayed_tasks:   number;
  high_risk_tasks: number;
  recommendations: string[];
  tasks:           Task[];
  load_percentage: number;
}

export interface CapacityReport {
  project_key:       string;
  team_capacity:     number;
  total_effort:      number;
  utilization:       number;
  is_overloaded:     boolean;
  bottleneck_report: { level: "ok" | "warning" | "critical"; message: string }[];
  workload:          { assignee: string; story_points: number; unit?: string }[];
}

// Karşılaştırma özeti tipi (YENİ)
export interface ProjectSummary {
  project_key:     string;
  total_tasks:     number;
  completed:       number;
  delayed:         number;
  high_risk:       number;
  average_risk:    number;
  sprint_status:   "LOW RISK" | "MEDIUM RISK" | "HIGH RISK";
  team_capacity:   number;
  total_effort:    number;
  utilization_pct: number;
  error?:          string;
}

// ── API Fonksiyonları ───────────────────────────────────────────────────────

// project_key parametresi eklendi — varsayılan "BAI"
export const analyzeSprint = (projectKey = "BAI") =>
  request<SprintAnalysis>(`/analyze/sprint?project_key=${projectKey}`);

export const analyzeCapacity = (projectKey = "BAI") =>
  request<CapacityReport>(`/analyze/capacity?project_key=${projectKey}`);

export const analyzeBrd = (projectKey = "BAI") =>
  get<{ source: string; project_key: string; total: number; average_score: number; low_alignment: number; high_alignment: number; tasks: Task[] }>(
    `/analyze/brd-report?project_key=${projectKey}`
  ).then((d) => ({ tasks: d.tasks as Task[] }));

export async function supportAsk(question: string, projectKey = "BAI"): Promise<string> {
  const data = await request<{ answer: string }>("/support/ask", {
    body: JSON.stringify({ question, project_key: projectKey }),
  });
  return data.answer;
}

// Çoklu proje karşılaştırma (YENİ)
export const compareProjects = (projectKeys: string[]) =>
  get<{ comparison: ProjectSummary[] }>(
    `/compare/sprint?projects=${projectKeys.join(",")}`
  ).then((d) => d.comparison);
