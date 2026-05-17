from fastapi import FastAPI, HTTPException
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

app = FastAPI(title="BAI AI Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
BRD_PATH       = os.path.join(BASE_DIR, "brd_document.md")
JIRA_EMAIL     = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_DOMAIN    = os.getenv("JIRA_DOMAIN")
JIRA_PROJECT   = os.getenv("JIRA_PROJECT_KEY", "BAI")
JIRA_URL       = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"
HEADERS        = {"Accept": "application/json", "Content-Type": "application/json"}


class SupportRequest(BaseModel):
    question: str

class BRDRequest(BaseModel):
    issue_key:   str
    summary:     str
    description: str = ""


def extract_text_from_adf(adf_data):
    if isinstance(adf_data, dict):
        if adf_data.get("type") == "text":
            return adf_data.get("text", "")
        if "content" in adf_data:
            return " ".join(extract_text_from_adf(c) for c in adf_data["content"])
    elif isinstance(adf_data, list):
        return " ".join(extract_text_from_adf(i) for i in adf_data)
    return ""


def fetch_jira_data() -> pd.DataFrame:
    payload = {
        "jql": f"project = '{JIRA_PROJECT}' ORDER BY created DESC",
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
        raise HTTPException(status_code=502, detail=f"Jira API error: {response.status_code}")

    issues_list = []
    for issue in response.json().get("issues", []):
        fields = issue.get("fields", {})
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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "project": JIRA_PROJECT}


@app.post("/analyze/sprint")
def analyze_sprint():
    df = fetch_jira_data()
    if df.empty:
        raise HTTPException(status_code=404, detail="No issues found.")
    df = run_all_agents(df)
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
    tasks_summary = df[cols].to_dict(orient="records")

    return {
        "sprint_status":   sprint_status,
        "average_risk":    round(average_risk, 2),
        "total_tasks":     context["total_tasks"],
        "completed_tasks": context["completed_tasks"],
        "delayed_tasks":   context["delayed_tasks"],
        "high_risk_tasks": context["high_risk_tasks"],
        "load_percentage": load_pct,
        "recommendations": recommendations,
        "tasks":           tasks_summary,
    }


@app.post("/analyze/capacity")
def analyze_capacity():
    df = fetch_jira_data()
    if df.empty:
        raise HTTPException(status_code=404, detail="No issues found.")
    df = run_all_agents(df)
    team_capacity, total_effort, bottleneck_raw = capacity_analysis(df)
    utilization = round(total_effort / team_capacity * 100, 1) if team_capacity else 0

    bottleneck_report = []
    for msg in bottleneck_raw:
        if "🚨" in msg:
            level = "critical"
        elif "⚠️" in msg:
            level = "warning"
        else:
            level = "ok"
        bottleneck_report.append({"level": level, "message": msg})

    workload = []
    if "assignee" in df.columns and "story_points" in df.columns:
        for assignee, group in df[df["assignee"] != "Unassigned"].groupby("assignee"):
            workload.append({"assignee": assignee, "story_points": int(group["story_points"].sum())})

    return {
        "team_capacity": float(team_capacity),
        "total_effort":  float(total_effort),
        "utilization":   utilization,
        "is_overloaded": bool(total_effort > team_capacity),
        "bottleneck_report": bottleneck_report,
        "workload":      workload,
    }


@app.post("/support/ask")
def support_ask(request: SupportRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    df    = fetch_jira_data()
    df    = run_all_agents(df) if not df.empty else df
    agent = JiraSupportAgent(df if not df.empty else None)
    return {"question": request.question, "answer": agent.ask(request.question)}


@app.get("/analyze/brd-report")
def get_brd_report():
    try:
        df = pd.read_csv(os.path.join(BASE_DIR, "brd_report.csv"))
        df["brd_score"] = df["brd_score"].apply(
            lambda x: 0 if x is None or (isinstance(x, float) and math.isnan(x)) else int(x)
        )
        df["brd_reasoning"] = df["brd_reasoning"].apply(
            lambda x: "" if x is None or (isinstance(x, float) and math.isnan(x)) else str(x)
        )
        return JSONResponse(content={
            "source": "cached",
            "total": len(df),
            "average_score": round(float(df["brd_score"].mean()), 1),
            "low_alignment": int((df["brd_score"] < 5).sum()),
            "high_alignment": int((df["brd_score"] >= 7).sum()),
            "tasks": df.to_dict(orient="records"),
        })
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="brd_report.csv not found. Run main.py first.")


@app.post("/analyze/brd-all")
def analyze_brd_all():
    df = fetch_jira_data()
    if df.empty:
        raise HTTPException(status_code=404, detail="No issues found.")
    df = run_brd_alignment(df, brd_path=BRD_PATH)
    cols = ["key", "summary", "status", "assignee", "sprint_name", "brd_score", "brd_reasoning"]
    result = df[cols].copy()
    result["brd_score"] = result["brd_score"].apply(lambda x: 0 if x is None or (isinstance(x, float) and math.isnan(x)) else int(x))
    result["brd_reasoning"] = result["brd_reasoning"].apply(lambda x: "" if x is None or (isinstance(x, float) and math.isnan(x)) else str(x))
    records = result.to_dict(orient="records")
    return JSONResponse(content={"tasks": records})


@app.post("/analyze/brd")
def analyze_brd(request: BRDRequest):
    if not request.summary.strip():
        raise HTTPException(status_code=400, detail="Summary cannot be empty.")
    brd_text  = load_brd_document(BRD_PATH)
    result    = call_openai_for_brd_score(request.summary, request.description, brd_text)
    score     = result["score"]
    reasoning = result["reasoning"]
    if 0 < score:
        add_brd_comment_to_jira(request.issue_key, score, reasoning)
    return {
        "issue_key":            request.issue_key,
        "brd_score":            score,
        "reasoning":            reasoning,
        "alignment_level":      "HIGH" if score >= 7 else "MEDIUM" if score >= 5 else "LOW",
        "jira_comment_written": score > 0,
    }
