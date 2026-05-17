"""
mcp_server.py
-------------
BAI — AI-Enhanced Jira Project Management
MCP (Model Context Protocol) Server

Transport: SSE → http://localhost:8001/sse
n8n connects to: https://<ngrok-url>/sse

Tools:
  jira_get_issues          — Fetch all issues from Jira
  jira_get_sprint_health   — Sprint risk + delay analysis
  jira_get_capacity_report — Team capacity vs workload
  jira_check_brd           — BRD alignment score for a single task
  jira_run_gap_detection   — BRD goals with no Jira task
  jira_ask_support         — Jira Support Agent chatbot

Run: python mcp_server.py
"""

import os, json, sys, requests
from requests.auth import HTTPBasicAuth
from typing import Optional
import pandas as pd
from pydantic import BaseModel, Field, ConfigDict
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(__file__))

from agents.risk_agent            import calculate_risk
from agents.capacity_agent        import capacity_analysis
from agents.recommendation_agent  import ai_recommendation
from agents.requirement_agent     import requirement_analysis
from agents.task_validation_agent import validate_task
from agents.brd_alignment_agent   import (
    call_openai_for_brd_score,
    add_brd_comment_to_jira,
    run_gap_detection,
    load_brd_document,
)
from agents.jira_support_agent import JiraSupportAgent

load_dotenv()

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
BRD_PATH       = os.path.join(BASE_DIR, "brd_document.md")
JIRA_EMAIL     = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
JIRA_DOMAIN    = os.getenv("JIRA_DOMAIN", "")
JIRA_PROJECT   = os.getenv("JIRA_PROJECT_KEY", "BAI")
JIRA_URL       = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"
HEADERS        = {"Accept": "application/json", "Content-Type": "application/json"}

mcp = FastMCP("jira_ai_mcp", host="0.0.0.0", port=8001)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_adf(adf) -> str:
    if isinstance(adf, dict):
        if adf.get("type") == "text":
            return adf.get("text", "")
        return " ".join(_extract_adf(c) for c in adf.get("content", []))
    if isinstance(adf, list):
        return " ".join(_extract_adf(i) for i in adf)
    return ""


def _fetch_issues(max_results: int = 100) -> pd.DataFrame:
    payload = {
        "jql": f"project = '{JIRA_PROJECT}' ORDER BY created DESC",
        "maxResults": max_results,
        "fields": ["summary","description","status","issuetype","priority",
                   "assignee","created","updated","parent",
                   "timeoriginalestimate","timespent",
                   "customfield_10016","customfield_10020","customfield_10139"],
    }
    resp = requests.post(JIRA_URL, headers=HEADERS,
                         auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
                         json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Jira API error: HTTP {resp.status_code}")

    rows = []
    for issue in resp.json().get("issues", []):
        f = issue["fields"]
        sp    = f.get("customfield_10016") or 0
        est_h = (f.get("timeoriginalestimate") or 0) / 3600 or sp * 2
        spt_h = (f.get("timespent") or 0) / 3600 or max(est_h - 1, 0)
        exp   = f.get("customfield_10139")
        exp   = exp.get("value","Unspecified") if isinstance(exp,dict) else (str(exp) if exp else "Unspecified")
        spf   = f.get("customfield_10020") or []
        sname = spf[-1].get("name","") if isinstance(spf,list) and spf else ""
        rows.append({
            "key":             issue["key"],
            "summary":         f.get("summary",""),
            "description":     _extract_adf(f.get("description")).strip(),
            "issue_type":      (f.get("issuetype") or {}).get("name","Unknown"),
            "status":          (f.get("status")    or {}).get("name","Unknown"),
            "assignee":        (f.get("assignee")  or {}).get("displayName","Unassigned"),
            "priority":        (f.get("priority")  or {}).get("name","None"),
            "expertise":       exp,
            "story_points":    sp,
            "sprint_name":     sname,
            "epic":            (f.get("parent") or {}).get("key",""),
            "estimated_hours": est_h,
            "spent_hours":     spt_h,
            "created":         (f.get("created") or "")[:10],
            "updated":         (f.get("updated") or "")[:10],
            "delay":           spt_h > est_h,
            "predicted_delay": est_h > 6,
        })
    return pd.DataFrame(rows)


def _run_agents(df):
    df = calculate_risk(df)
    df = ai_recommendation(df)
    df = requirement_analysis(df)
    df = validate_task(df)
    return df


# ── Tool 1: Get Issues ────────────────────────────────────────────────────────

class GetIssuesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_results:   int           = Field(default=50, ge=1, le=200)
    status_filter: Optional[str] = Field(default=None)

@mcp.tool(name="jira_get_issues", annotations={"readOnlyHint": True, "destructiveHint": False})
async def jira_get_issues(params: GetIssuesInput) -> str:
    """Fetches issues from Jira and returns a structured summary."""
    try:
        df = _fetch_issues(params.max_results)
        df = calculate_risk(df)
        if params.status_filter:
            df = df[df["status"].str.lower() == params.status_filter.lower()]
        return json.dumps({
            "project": JIRA_PROJECT, "total": len(df),
            "status_counts": df["status"].value_counts().to_dict(),
            "issues": df[["key","summary","status","assignee","issue_type",
                           "story_points","sprint_name","risk_score"]].to_dict(orient="records"),
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool 2: Sprint Health ─────────────────────────────────────────────────────

class SprintHealthInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sprint_name:    Optional[str] = Field(default=None)
    min_risk_score: float         = Field(default=2.5, ge=0, le=5)

@mcp.tool(name="jira_get_sprint_health", annotations={"readOnlyHint": True, "destructiveHint": False})
async def jira_get_sprint_health(params: SprintHealthInput) -> str:
    """Analyzes sprint health: risk scores, delays, and recommendations."""
    try:
        df = _fetch_issues()
        df = _run_agents(df)
        if params.sprint_name:
            df = df[df["sprint_name"].str.lower() == params.sprint_name.lower()]
            if df.empty:
                return json.dumps({"error": f"Sprint not found: {params.sprint_name}"})
        avg   = float(df["risk_score"].mean())
        level = "LOW RISK" if avg < 1.5 else "MEDIUM RISK" if avg < 2.5 else "HIGH RISK"
        recs  = []
        if len(df[df["risk_score"] >= params.min_risk_score]) > 2: recs.append("Add more developers to sprint")
        if int(df["delay"].sum()) > 2:                              recs.append("Review planning accuracy")
        if avg > 2.5:                                               recs.append("Reduce sprint workload")
        return json.dumps({
            "sprint_filter": params.sprint_name or "all",
            "sprint_status": level, "average_risk": round(avg,2),
            "total_tasks": len(df), "delayed_tasks": int(df["delay"].sum()),
            "high_risk_tasks": int((df["risk_score"] >= params.min_risk_score).sum()),
            "recommendations": recs,
            "tasks": df[["key","summary","status","assignee","risk_score",
                          "delay","recommendation","validation_result","sprint_name"]].to_dict(orient="records"),
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool 3: Capacity Report ───────────────────────────────────────────────────

class CapacityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sprint_name: Optional[str] = Field(default=None)

@mcp.tool(name="jira_get_capacity_report", annotations={"readOnlyHint": True, "destructiveHint": False})
async def jira_get_capacity_report(params: CapacityInput) -> str:
    """Compares team workload against capacity and identifies bottlenecks."""
    try:
        df = _fetch_issues()
        df = _run_agents(df)
        if params.sprint_name:
            df = df[df["sprint_name"].str.lower() == params.sprint_name.lower()]
        cap, effort, bottleneck = capacity_analysis(df)
        return json.dumps({
            "sprint_filter": params.sprint_name or "all",
            "team_capacity_hours": float(cap), "total_effort_hours": float(effort),
            "utilization_pct": round(effort/cap*100,1) if cap else 0,
            "is_overloaded": bool(effort > cap), "bottleneck_report": bottleneck,
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool 4: BRD Check (individual args — n8n compatible) ─────────────────────

@mcp.tool(name="jira_check_brd", annotations={"readOnlyHint": False, "destructiveHint": False})
async def jira_check_brd(
    issue_key: str,
    summary: str,
    description: str = "",
    post_comment: bool = True
) -> str:
    """
    Calculates a 1-10 BRD alignment score for a Jira task.
    Posts the result as a Jira comment if post_comment is True.

    Args:
        issue_key: Jira key e.g. 'BAI-42'
        summary: Issue title
        description: Issue description (optional)
        post_comment: Post result to Jira as comment (default True)
    """
    try:
        brd = load_brd_document(BRD_PATH)
        res = call_openai_for_brd_score(summary, description, brd)
        wrote = False
        if post_comment and res["score"] > 0:
            add_brd_comment_to_jira(issue_key, res["score"], res["reasoning"])
            wrote = True
        return json.dumps({
            "issue_key":            issue_key,
            "brd_score":            res["score"],
            "alignment_level":      "HIGH" if res["score"] >= 7 else "MEDIUM" if res["score"] >= 5 else "LOW",
            "reasoning":            res["reasoning"],
            "jira_comment_written": wrote,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool 5: Gap Detection ─────────────────────────────────────────────────────

class GapInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    brd_path: str = Field(default=BRD_PATH)

@mcp.tool(name="jira_run_gap_detection", annotations={"readOnlyHint": True, "destructiveHint": False})
async def jira_run_gap_detection(params: GapInput) -> str:
    """Finds BRD goals that have no corresponding Jira task."""
    try:
        df   = _fetch_issues()
        gaps = run_gap_detection(df, brd_path=params.brd_path)
        return json.dumps({"gap_count": len(gaps), "all_covered": len(gaps)==0, "gaps": gaps}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool 6: Support Agent ─────────────────────────────────────────────────────

class SupportInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    question: str = Field(..., min_length=3, max_length=500)

@mcp.tool(name="jira_ask_support", annotations={"readOnlyHint": True, "destructiveHint": False})
async def jira_ask_support(params: SupportInput) -> str:
    """Answers questions about Jira or the current sprint state."""
    try:
        df    = _fetch_issues()
        df    = _run_agents(df)
        agent = JiraSupportAgent(df)
        return json.dumps({"question": params.question, "answer": agent.ask(params.question)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool 7: Assignee Suggestion ──────────────────────────────────────────────

@mcp.tool(name="jira_suggest_assignee", annotations={"readOnlyHint": False, "destructiveHint": False})
async def jira_suggest_assignee(
    issue_key: str,
    summary: str,
    description: str = "",
    issue_type: str = ""
) -> str:
    """
    Suggests the best team member to assign to an unassigned Jira task.
    Analyzes team expertise and current workload, then posts a comment to Jira.

    Args:
        issue_key: Jira key e.g. 'BAI-50'
        summary: Issue title
        description: Issue description (optional)
        issue_type: Issue type e.g. 'Story', 'Task' (optional)
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Fetch team workload from Jira
        df = _fetch_issues()
        df = calculate_risk(df)

        # Build team context — skip Unassigned
        team_context = {}
        for assignee, group in df[df["assignee"] != "Unassigned"].groupby("assignee"):
            expertise_mode = group["expertise"].mode()
            team_context[assignee] = {
                "primary_expertise": expertise_mode[0] if not expertise_mode.empty else "Unknown",
                "active_tasks":      len(group[group["status"].isin(["Devam Ediyor", "In Progress"])]),
                "total_tasks":       len(group),
                "total_story_points": int(group["story_points"].sum()),
                "high_risk_tasks":   int((group["risk_score"] >= 2.5).sum()),
            }

        if not team_context:
            return json.dumps({"error": "No assigned team members found in Jira."})

        prompt = f"""You are a Project Manager assigning Jira tasks to the right team member.

New Task:
- Key: {issue_key}
- Summary: {summary}
- Description: {description if description else "No description provided."}
- Type: {issue_type if issue_type else "Unknown"}

Team members and current workload:
{json.dumps(team_context, indent=2)}

PRIORITY RULES (in order):
1. EXPERTISE MATCH is the most important factor — always assign to someone whose primary_expertise matches the task requirements
2. Among matching experts, prefer the one with fewer active_tasks
3. Only consider non-matching experts if NO matching expert exists

Respond ONLY in this exact format:
SUGGESTED_ASSIGNEE: <full name>
REASON: <one sentence explaining expertise match and availability>"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.2
        )
        text = response.choices[0].message.content.strip()

        suggested, reason = "", ""
        for line in text.splitlines():
            if line.startswith("SUGGESTED_ASSIGNEE:"):
                suggested = line.replace("SUGGESTED_ASSIGNEE:", "").strip()
            elif line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()

        # Post comment to Jira
        comment_text = (
            f"🤖 AI Assignee Suggestion\n\n"
            f"Suggested Assignee: {suggested}\n\n"
            f"Reason: {reason}\n\n"
            f"📊 This suggestion is based on team expertise and current workload analysis.\n"
            f"⚠️ Please review and assign manually if needed."
        )
        comment_url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{issue_key}/comment"
        payload = {
            "body": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment_text}]}]
            }
        }
        resp = requests.post(
            comment_url, headers=HEADERS,
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN), json=payload
        )
        comment_posted = resp.status_code == 201

        return json.dumps({
            "issue_key":        issue_key,
            "suggested_assignee": suggested,
            "reason":           reason,
            "comment_posted":   comment_posted,
            "team_context":     team_context,
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool 8: Overload Warning ──────────────────────────────────────────────────

@mcp.tool(name="jira_warn_overload", annotations={"readOnlyHint": False, "destructiveHint": False})
async def jira_warn_overload(
    issue_key: str,
    assignee_name: str,
    summary: str = "",
    description: str = ""
) -> str:
    """
    Checks if the assigned team member is overloaded OR has wrong expertise.
    Posts a warning comment to Jira if either issue is detected.
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        df = _fetch_issues()
        df = calculate_risk(df)

        person = df[df["assignee"].str.lower() == assignee_name.lower()]
        if person.empty:
            return json.dumps({"message": f"No data found for {assignee_name}", "warning_posted": False})

        expertise_mode   = person["expertise"].mode()
        person_expertise = expertise_mode[0] if not expertise_mode.empty else "Unknown"
        active_tasks     = int((person["status"].isin(["Devam Ediyor", "In Progress"])).sum())
        total_sp         = int(person["story_points"].sum())
        high_risk        = int((person["risk_score"] >= 2.5).sum())
        is_overloaded    = active_tasks > 3 or total_sp > 20

        task_url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{issue_key}?fields=customfield_10139"
        task_resp = requests.get(
            task_url, headers=HEADERS,
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
        )
        required_expertise = ""
        if task_resp.status_code == 200:
            exp_raw = task_resp.json().get("fields", {}).get("customfield_10139")
            if isinstance(exp_raw, dict):
                required_expertise = exp_raw.get("value", "")
            elif exp_raw:
                required_expertise = str(exp_raw)

        if not required_expertise and summary:
            prompt = f"""What expertise is needed for this Jira task?
Summary: {summary}
Description: {description if description else "No description."}
Options: Backend, Frontend, QA/Test, Database, Business Analysis, Project Management
Respond with ONLY one option from the list."""
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.1
            )
            required_expertise = response.choices[0].message.content.strip()

        is_match = (
            not required_expertise or
            required_expertise.lower() == person_expertise.lower()
        )
        mismatch_reason = (
            "" if is_match
            else f"Task requires {required_expertise} but {assignee_name} primarily works on {person_expertise}."
        )

        warnings = []
        if is_overloaded:
            warnings.append(
                f"🔴 Overload Warning: {assignee_name} has {active_tasks} active tasks "
                f"and {total_sp} story points assigned. Consider redistributing."
            )
        if not is_match:
            warnings.append(
                f"⚠️ Expertise Mismatch: This task requires {required_expertise} expertise, "
                f"but {assignee_name} primarily works on {person_expertise}. "
                f"{mismatch_reason}"
            )

        if not warnings:
            return json.dumps({
                "assignee":           assignee_name,
                "person_expertise":   person_expertise,
                "required_expertise": required_expertise,
                "overloaded":         False,
                "expertise_match":    True,
                "warning_posted":     False,
                "message":            "Assignment looks correct."
            })

        comment_text = (
            f"🤖 AI Assignment Quality Check — {assignee_name}\n\n"
            + "\n\n".join(warnings)
            + f"\n\n📊 Analysis based on team expertise learned from Jira history."
        )

        url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{issue_key}/comment"
        payload = {
            "body": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment_text}]}]
            }
        }
        resp = requests.post(url, headers=HEADERS,
                             auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN), json=payload)

        return json.dumps({
            "assignee":           assignee_name,
            "person_expertise":   person_expertise,
            "required_expertise": required_expertise,
            "overloaded":         is_overloaded,
            "expertise_match":    is_match,
            "warning_posted":     resp.status_code == 201,
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})

# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀  BAI MCP Server starting...")
    print(f"    Project  : {JIRA_PROJECT}")
    print(f"    Domain   : {JIRA_DOMAIN}")
    print(f"    Endpoint : http://localhost:8001/sse")
    print()
    mcp.run(transport="sse")