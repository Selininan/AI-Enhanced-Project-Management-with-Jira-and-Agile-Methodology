from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import math
from pydantic import BaseModel
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

from agents.risk_agent import calculate_risk
from agents.capacity_agent import capacity_analysis
from agents.recommendation_agent import ai_recommendation
from agents.requirement_agent import requirement_analysis
from agents.task_validation_agent import validate_task
from agents.jira_support_agent import JiraSupportAgent
from agents.brd_alignment_agent import call_openai_for_brd_score, add_brd_comment_to_jira, load_brd_document, run_brd_alignment
from context.context_builder import build_context

load_dotenv()

app = FastAPI(title="BAI AI Agent API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
BRD_PATH        = os.path.join(BASE_DIR, "brd_document.md")
JIRA_EMAIL      = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN  = os.getenv("JIRA_API_TOKEN")
JIRA_DOMAIN     = os.getenv("JIRA_DOMAIN")
DEFAULT_PROJECT = os.getenv("JIRA_PROJECT_KEY", "BAI")
JIRA_URL        = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"
HEADERS         = {"Accept": "application/json", "Content-Type": "application/json"}


# ── Request / Response Models ──────────────────────────────────────────────────

class SupportRequest(BaseModel):
    question:    str
    project_key: str = DEFAULT_PROJECT   # hangi projeyi sorsun?

class BRDRequest(BaseModel):
    issue_key:   str
    summary:     str
    description: str = ""
    project_key: str = DEFAULT_PROJECT


# ── Helpers ────────────────────────────────────────────────────────────────────

def extract_text_from_adf(adf_data):
    if isinstance(adf_data, dict):
        if adf_data.get("type") == "text":
            return adf_data.get("text", "")
        if "content" in adf_data:
            return " ".join(extract_text_from_adf(c) for c in adf_data["content"])
    elif isinstance(adf_data, list):
        return " ".join(extract_text_from_adf(i) for i in adf_data)
    return ""


def fetch_jira_data(project_key: str) -> pd.DataFrame:
    """Verilen project_key için Jira'dan issue'ları çeker."""
    payload = {
        "jql": f"project = '{project_key}' ORDER BY created DESC",
        "maxResults": 100,
        "fields": [
            "summary", "description", "status", "issuetype",
            "priority", "assignee", "created", "updated",
            "parent", "timeoriginalestimate", "timespent",
            "customfield_10016", "customfield_10020", "customfield_10139"
        ]
    }
    response = requests.post(
        JIRA_URL, headers=HEADERS,
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN), json=payload
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Jira API error for project '{project_key}': HTTP {response.status_code}"
        )

    issues_list = []
    for issue in response.json().get("issues", []):
        fields        = issue.get("fields", {})
        desc_data     = fields.get("description")
        description   = extract_text_from_adf(desc_data).strip() if desc_data else ""
        assignee_data = fields.get("assignee")
        assignee      = assignee_data["displayName"] if assignee_data else "Unassigned"
        exp_raw       = fields.get("customfield_10139")
        expertise     = (
            exp_raw.get("value", "Unspecified") if isinstance(exp_raw, dict)
            else str(exp_raw) if exp_raw else "Unspecified"
        )
        sprint_field  = fields.get("customfield_10020") or []
        sprint_name   = sprint_field[-1].get("name", "") if isinstance(sprint_field, list) and sprint_field else ""
        est_sec       = fields.get("timeoriginalestimate")
        spent_sec     = fields.get("timespent")
        story_points  = fields.get("customfield_10016") or 0
        est_h         = (est_sec / 3600) if est_sec else story_points * 2
        spent_h       = (spent_sec / 3600) if spent_sec else max(est_h - 1, 0)
        parent_data   = fields.get("parent")

        issues_list.append({
            "key":             issue.get("key", ""),
            "summary":         fields.get("summary", ""),
            "description":     description,
            "status":          (fields.get("status") or {}).get("name", "Unknown"),
            "issue_type":      (fields.get("issuetype") or {}).get("name", "Unknown"),
            "priority":        (fields.get("priority") or {}).get("name", "None"),
            "assignee":        assignee,
            "expertise":       expertise,
            "sprint_name":     sprint_name,
            "created":         (fields.get("created") or "")[:10],
            "updated":         (fields.get("updated") or "")[:10],
            "epic":            (parent_data or {}).get("key", ""),
            "story_points":    story_points,
            "estimated_hours": est_h,
            "spent_hours":     spent_h,
        })

    df = pd.DataFrame(issues_list)
    if df.empty:
        return df

    df["estimated_hours"] = df.apply(
        lambda r: r["estimated_hours"] if r["estimated_hours"] > 0 else r["story_points"] * 2, axis=1
    )
    df["spent_hours"] = df.apply(
        lambda r: r["spent_hours"] if r["spent_hours"] > 0 else max(r["estimated_hours"] - 1, 0), axis=1
    )
    df["delay"]           = df["spent_hours"] > df["estimated_hours"]
    df["predicted_delay"] = df["estimated_hours"].apply(lambda h: h > 6)
    return df


def run_all_agents(df):
    df = calculate_risk(df)
    df = ai_recommendation(df)
    df = requirement_analysis(df)
    df = validate_task(df)
    return df


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "default_project": DEFAULT_PROJECT}


@app.get("/projects")
def list_projects():
    """
    Jira'daki erişilebilir projeleri listeler.
    Frontend dropdown için kullanılabilir.
    """
    url  = f"https://{JIRA_DOMAIN}/rest/api/3/project/search?maxResults=50&action=browse"
    resp = requests.get(url, headers=HEADERS, auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN))
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Jira project list failed")
    projects = [
        {"key": p["key"], "name": p["name"]}
        for p in resp.json().get("values", [])
    ]
    return {"projects": projects}


@app.post("/analyze/sprint")
def analyze_sprint(
    project_key: str = Query(
        default=DEFAULT_PROJECT,
        description="Jira project key, e.g. BAI, DT, DEV"
    )
):
    """
    Sprint risk raporu.
    Kullanim: POST /analyze/sprint?project_key=DT
    """
    df = fetch_jira_data(project_key)
    if df.empty:
        return {
            "project_key": project_key, "sprint_status": "LOW RISK",
            "average_risk": 0, "total_tasks": 0, "completed_tasks": 0,
            "delayed_tasks": 0, "high_risk_tasks": 0, "load_percentage": 0,
            "recommendations": [f"No tasks found in project '{project_key}'."], "tasks": [],
        }
    df            = run_all_agents(df)
    context       = build_context(df)
    average_risk  = float(df["risk_score"].mean())
    team_capacity, total_effort, _ = capacity_analysis(df)
    load_pct      = round(total_effort / team_capacity * 100, 1) if team_capacity else 0
    sprint_status = "LOW RISK" if average_risk < 1 else "MEDIUM RISK" if average_risk < 2 else "HIGH RISK"
    delayed_tasks   = df[df["delay"] == True]
    high_risk_tasks = df[df["risk_score"] >= 3]
    recommendations = []
    if len(high_risk_tasks) > 2: recommendations.append("Add more developers to sprint")
    if len(delayed_tasks) > 2:   recommendations.append("Review planning accuracy")
    if average_risk > 2:         recommendations.append("Reduce sprint workload")

    cols = ["key", "summary", "status", "assignee", "risk_score",
            "delay", "sprint_name", "recommendation", "validation_result"]
    if "brd_score" in df.columns:
        cols += ["brd_score", "brd_reasoning"]

    return {
        "project_key":     project_key,
        "sprint_status":   sprint_status,
        "average_risk":    round(average_risk, 2),
        "total_tasks":     context["total_tasks"],
        "completed_tasks": context["completed_tasks"],
        "delayed_tasks":   context["delayed_tasks"],
        "high_risk_tasks": context["high_risk_tasks"],
        "load_percentage": load_pct,
        "recommendations": recommendations,
        "tasks":           df[cols].to_dict(orient="records"),
    }


@app.post("/analyze/capacity")
def analyze_capacity(
    project_key: str = Query(
        default=DEFAULT_PROJECT,
        description="Jira project key"
    )
):
    """
    Kapasite raporu.
    Kullanim: POST /analyze/capacity?project_key=DEV
    """
    df = fetch_jira_data(project_key)
    if df.empty:
        return {
            "project_key": project_key, "team_capacity": 0, "total_effort": 0,
            "utilization": 0, "is_overloaded": False, "bottleneck_report": [], "workload": [],
        }
    df = run_all_agents(df)
    team_capacity, total_effort, bottleneck_raw = capacity_analysis(df)
    utilization = round(total_effort / team_capacity * 100, 1) if team_capacity else 0

    bottleneck_report = []
    for msg in bottleneck_raw:
        level = "critical" if "🚨" in msg else "warning" if "⚠️" in msg else "ok"
        bottleneck_report.append({"level": level, "message": msg})

    use_hours = df["story_points"].sum() == 0
    workload = []
    if "assignee" in df.columns:
        for assignee, group in df[df["assignee"] != "Unassigned"].groupby("assignee"):
            workload.append({
                "assignee":     assignee,
                "story_points": round(float(group["estimated_hours"].sum()), 1) if use_hours else int(group["story_points"].sum()),
                "unit":         "h" if use_hours else "pts",
            })

    return {
        "project_key":       project_key,
        "team_capacity":     float(team_capacity),
        "total_effort":      float(total_effort),
        "utilization":       utilization,
        "is_overloaded":     bool(total_effort > team_capacity),
        "bottleneck_report": bottleneck_report,
        "workload":          workload,
    }


@app.post("/support/ask")
def support_ask(request: SupportRequest):
    """
    AI Jira destek sorusu.
    Body'de project_key ile proje bazlı bağlam verilir.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    df    = fetch_jira_data(request.project_key)
    df    = run_all_agents(df) if not df.empty else df
    agent = JiraSupportAgent(df if not df.empty else None)
    return {
        "project_key": request.project_key,
        "question":    request.question,
        "answer":      agent.ask(request.question),
    }


@app.get("/analyze/brd-report")
def get_brd_report(
    project_key: str = Query(default=DEFAULT_PROJECT)
):
    """
    Onceden uretilmis brd_report.csv okur.
    Her proje icin ayri CSV: brd_report_DT.csv, brd_report_BAI.csv
    """
    csv_name = f"brd_report_{project_key}.csv"
    csv_path = os.path.join(BASE_DIR, csv_name)
    try:
        df = pd.read_csv(csv_path)
        df["brd_score"] = df["brd_score"].apply(
            lambda x: 0 if x is None or (isinstance(x, float) and math.isnan(x)) else int(x)
        )
        df["brd_reasoning"] = df["brd_reasoning"].apply(
            lambda x: "" if x is None or (isinstance(x, float) and math.isnan(x)) else str(x)
        )
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].fillna("")
        for col in df.select_dtypes(include="number").columns:
            df[col] = df[col].fillna(0)
        return JSONResponse(content={
            "source":        "cached",
            "project_key":   project_key,
            "total":         len(df),
            "average_score": round(float(df["brd_score"].mean()), 1),
            "low_alignment": int((df["brd_score"] < 5).sum()),
            "high_alignment": int((df["brd_score"] >= 7).sum()),
            "tasks":         df.to_dict(orient="records"),
        })
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"brd_report_{project_key}.csv not found. Run: python3 main.py {project_key}")


@app.post("/analyze/brd-all")
def analyze_brd_all(
    project_key: str = Query(default=DEFAULT_PROJECT)
):
    """Tum proje issue'lari icin BRD skoru hesaplar, proje bazli CSV kaydeder."""
    df = fetch_jira_data(project_key)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No issues found in project '{project_key}'")
    df = run_brd_alignment(df, brd_path=BRD_PATH)

    csv_name = f"brd_report_{project_key}.csv"
    df[["key", "summary", "brd_score", "brd_reasoning"]].to_csv(
        os.path.join(BASE_DIR, csv_name), index=False
    )

    cols   = ["key", "summary", "status", "assignee", "sprint_name", "brd_score", "brd_reasoning"]
    result = df[cols].copy()
    result["brd_score"] = result["brd_score"].apply(
        lambda x: 0 if x is None or (isinstance(x, float) and math.isnan(x)) else int(x)
    )
    result["brd_reasoning"] = result["brd_reasoning"].apply(
        lambda x: "" if x is None or (isinstance(x, float) and math.isnan(x)) else str(x)
    )
    return JSONResponse(content={"project_key": project_key, "tasks": result.to_dict(orient="records")})


@app.post("/analyze/brd")
def analyze_brd(request: BRDRequest):
    """Tek bir issue icin BRD skoru hesaplar."""
    if not request.summary.strip():
        raise HTTPException(status_code=400, detail="Summary cannot be empty.")
    brd_text  = load_brd_document(BRD_PATH)
    result    = call_openai_for_brd_score(request.summary, request.description, brd_text)
    score     = result["score"]
    reasoning = result["reasoning"]
    if score > 0:
        add_brd_comment_to_jira(request.issue_key, score, reasoning)
    return {
        "project_key":          request.project_key,
        "issue_key":            request.issue_key,
        "brd_score":            score,
        "reasoning":            reasoning,
        "alignment_level":      "HIGH" if score >= 7 else "MEDIUM" if score >= 5 else "LOW",
        "jira_comment_written": score > 0,
    }


# ── Multi-project karsilastirma endpoint'i (YENİ) ─────────────────────────────

@app.get("/compare/sprint")
def compare_projects(
    projects: str = Query(
        default="BAI,DT",
        description="Virgülle ayrilmis proje key'leri, örn: BAI,DT,DEV"
    )
):
    """
    Birden fazla projeyi ayni anda analiz edip karsilastirmali ozet doner.
    Kullanim: GET /compare/sprint?projects=BAI,DT,DEV
    """
    keys = [k.strip().upper() for k in projects.split(",") if k.strip()]
    if not keys:
        raise HTTPException(status_code=400, detail="At least one project key required.")

    results = []
    for key in keys:
        try:
            df = fetch_jira_data(key)
            if df.empty:
                results.append({"project_key": key, "error": "No issues found"})
                continue
            df       = run_all_agents(df)
            avg_risk = float(df["risk_score"].mean())
            team_cap, effort, _ = capacity_analysis(df)
            results.append({
                "project_key":     key,
                "total_tasks":     len(df),
                "completed":       int((df["status"].isin(["Tamam", "Done", "Tamamlandi"])).sum()),
                "delayed":         int(df["delay"].sum()),
                "high_risk":       int((df["risk_score"] >= 3).sum()),
                "average_risk":    round(avg_risk, 2),
                "sprint_status":   "LOW RISK" if avg_risk < 1 else "MEDIUM RISK" if avg_risk < 2 else "HIGH RISK",
                "team_capacity":   float(team_cap),
                "total_effort":    float(effort),
                "utilization_pct": round(effort / team_cap * 100, 1) if team_cap else 0,
            })
        except Exception as e:
            results.append({"project_key": key, "error": str(e)})

    return {"comparison": results}
