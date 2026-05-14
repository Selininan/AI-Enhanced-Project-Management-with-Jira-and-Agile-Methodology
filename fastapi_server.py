from fastapi import FastAPI, HTTPException
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
from agents.jira_support_agent import jira_support_answer
from agents.brd_alignment_agent import call_claude_for_brd_score, add_brd_comment_to_jira
from context.context_builder import build_context

load_dotenv()

app = FastAPI(title="BAI AI Agent API", version="1.0.0")

JIRA_EMAIL     = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_DOMAIN    = os.getenv("JIRA_DOMAIN")
JIRA_PROJECT   = os.getenv("JIRA_PROJECT_KEY", "BAI")
JIRA_URL       = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}


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
            "customfield_10016", "customfield_10139"
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
        desc_data = fields.get("description")
        description_text = extract_text_from_adf(desc_data).strip() if desc_data else ""
        assignee_data = fields.get("assignee")
        assignee_name = assignee_data["displayName"] if assignee_data else "Unassigned"
        expertise_data = fields.get("customfield_10139")
        if isinstance(expertise_data, dict):
            expertise = expertise_data.get("value", "Belirtilmemiş")
        elif expertise_data:
            expertise = str(expertise_data)
        else:
            expertise = "Belirtilmemiş"
        estimated_seconds = fields.get("timeoriginalestimate")
        spent_seconds     = fields.get("timespent")
        story_points      = fields.get("customfield_10016")
        estimated_hours = (estimated_seconds / 3600) if estimated_seconds else 0
        spent_hours     = (spent_seconds / 3600)     if spent_seconds     else 0
        parent_data = fields.get("parent")
        epic_value  = parent_data.get("key", "") if isinstance(parent_data, dict) else ""
        issues_list.append({
            "key": issue.get("key", ""),
            "summary": fields.get("summary", ""),
            "description": description_text,
            "status": fields["status"]["name"]    if fields.get("status")    else "Unknown",
            "issue_type": fields["issuetype"]["name"] if fields.get("issuetype") else "Unknown",
            "priority": fields["priority"]["name"]  if fields.get("priority")  else "None",
            "assignee": assignee_name,
            "expertise": expertise,
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "epic": epic_value,
            "story_points": story_points if story_points else 0,
            "estimated_hours": estimated_hours,
            "spent_hours": spent_hours
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


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "project": JIRA_PROJECT}


@app.post("/analyze/sprint")
def analyze_sprint():
    df = fetch_jira_data()
    if df.empty:
        raise HTTPException(status_code=404, detail="No issues found.")
    df = run_all_agents(df)
    context      = build_context(df)
    average_risk = df["risk_score"].mean()
    sprint_status = "LOW RISK" if average_risk < 1 else "MEDIUM RISK" if average_risk < 2 else "HIGH RISK"
    delayed_tasks   = df[df["delay"] == True]
    high_risk_tasks = df[df["risk_score"] >= 3]
    recommendations = []
    if len(high_risk_tasks) > 2: recommendations.append("Add more developers to sprint")
    if len(delayed_tasks) > 2:   recommendations.append("Review planning accuracy")
    if average_risk > 2:         recommendations.append("Reduce sprint workload")
    df["delay"] = df["delay"].astype(bool)
    tasks_summary = df[[
        "key", "summary", "status", "assignee",
        "risk_score", "delay", "recommendation", "validation_result"
    ]].to_dict(orient="records")
    return {
        "sprint_status": sprint_status,
        "average_risk": round(average_risk, 2),
        "total_tasks": context["total_tasks"],
        "completed_tasks": context["completed_tasks"],
        "delayed_tasks": context["delayed_tasks"],
        "high_risk_tasks": context["high_risk_tasks"],
        "recommendations": recommendations,
        "tasks": tasks_summary
    }


@app.post("/analyze/capacity")
def analyze_capacity():
    df = fetch_jira_data()
    if df.empty:
        raise HTTPException(status_code=404, detail="No issues found.")
    df = run_all_agents(df)
    team_capacity, total_effort, bottleneck_report = capacity_analysis(df)
    return {
        "team_capacity_hours": float(team_capacity),
        "total_effort_hours":  float(total_effort),
        "is_overloaded":       bool(total_effort > team_capacity),
        "bottleneck_report":   bottleneck_report
    }


@app.post("/support/ask")
def support_ask(request: SupportRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    return {"question": request.question, "answer": jira_support_answer(request.question)}


@app.post("/analyze/brd")
def analyze_brd(request: BRDRequest):
    """
    Tek bir task için BRD uyum skoru hesaplar.
    n8n tarafından issue_created event'inde otomatik çağrılır.
    Score < 5 ise Jira'ya otomatik comment yazar.
    """
    if not request.summary.strip():
        raise HTTPException(status_code=400, detail="Summary cannot be empty.")

    result    = call_claude_for_brd_score(request.summary, request.description)
    score     = result["score"]
    reasoning = result["reasoning"]

    jira_comment_written = False
    if 0 < score < 5:
        add_brd_comment_to_jira(request.issue_key, score, reasoning)
        jira_comment_written = True

    return {
        "issue_key":            request.issue_key,
        "brd_score":            score,
        "reasoning":            reasoning,
        "alignment_level":      "HIGH" if score >= 7 else "MEDIUM" if score >= 5 else "LOW",
        "jira_comment_written": jira_comment_written
    }