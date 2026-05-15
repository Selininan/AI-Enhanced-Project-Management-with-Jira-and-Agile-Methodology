"""
brd_alignment_agent.py
----------------------
Two main responsibilities:

1. SCORING       — Calculates a BRD alignment score (1-10) for each Jira task.
                   Automatically posts a Jira comment for tasks scoring below 5.

2. GAP DETECTION — Scans every goal in the BRD and reports goals that have
                   no corresponding Jira task (missing coverage).

The BRD is not hardcoded — it is read dynamically from brd_document.md.
To update the BRD, edit that file only; no code changes are needed.
"""

import os
import re
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JIRA_EMAIL     = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_DOMAIN    = os.getenv("JIRA_DOMAIN")

client = OpenAI(api_key=OPENAI_API_KEY)


# ══════════════════════════════════════════════════════════════════════════
# 1. LOAD BRD DOCUMENT
# ══════════════════════════════════════════════════════════════════════════

def load_brd_document(path: str = "brd_document.md") -> str:
    """
    Reads brd_document.md and returns its content as a string.
    Raises a descriptive FileNotFoundError if the file is missing.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"BRD document not found: {path}\n"
            "Make sure brd_document.md exists in the project root directory."
        )
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    print(f"📄  BRD document loaded: {path} ({len(content)} characters)")
    return content


def extract_brd_goals(brd_text: str) -> list[dict]:
    """
    Parses GOAL-XX headings and their descriptions from the BRD text.
    Returns a list of {"id": "GOAL-01", "title": "...", "description": "..."} dicts.
    """
    goals = []
    # Find all GOAL-XX headings
    pattern = re.compile(r"###\s+(GOAL-\d+)\s+—\s+(.+?)(?=###\s+GOAL-|\Z)", re.DOTALL)
    for match in pattern.finditer(brd_text):
        goal_id    = match.group(1).strip()
        rest       = match.group(2)
        # First line is the title, the rest is the description
        lines      = rest.strip().splitlines()
        title      = lines[0].strip()
        description = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        goals.append({"id": goal_id, "title": title, "description": description[:500]})
    return goals


# ══════════════════════════════════════════════════════════════════════════
# 2. TASK SCORING — BRD alignment score per task
# ══════════════════════════════════════════════════════════════════════════

def call_openai_for_brd_score(
    task_summary: str,
    task_description: str,
    brd_text: str
) -> dict:
    """
    Sends the task details and BRD to OpenAI and returns a 1-10 alignment score.
    Returns: {"score": int, "reasoning": str}
    """
    prompt = f"""You are a Business Analyst evaluating a Jira task against a Business Requirements Document (BRD).

--- BRD DOCUMENT START ---
{brd_text[:3000]}
--- BRD DOCUMENT END ---

Task to evaluate:
- Summary: {task_summary}
- Description: {task_description if task_description else "No description provided."}

Instructions:
1. Analyze how well this task contributes to the BRD goals above.
2. Assign a score from 1 to 10 (1 = no alignment, 10 = perfect alignment).
3. Write a short 1-2 sentence reasoning in English explaining the score.
4. If the task description is empty or very vague, lower the score accordingly.

Respond ONLY in this exact format (no extra text):
SCORE: <number>
REASONING: <one or two sentences>"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.2
        )
        text = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[OpenAI ERROR] {e}")
        return {"score": 0, "reasoning": f"OpenAI API error: {e}"}

    score, reasoning = 0, ""
    for line in text.splitlines():
        if line.startswith("SCORE:"):
            try:
                score = int(line.replace("SCORE:", "").strip())
            except ValueError:
                score = 0
        elif line.startswith("REASONING:"):
            reasoning = line.replace("REASONING:", "").strip()

    return {"score": score, "reasoning": reasoning}


def add_brd_comment_to_jira(issue_key: str, score: int, reasoning: str):
    """Posts the BRD alignment score as a comment on the Jira issue."""
    if score >= 7:
        label = "✅ HIGH ALIGNMENT"
    elif score >= 5:
        label = "⚠️ MEDIUM ALIGNMENT"
    else:
        label = "🚨 LOW ALIGNMENT"

    comment_text = (
        f"🤖 BRD Alignment Analysis\n\n"
        f"Score: {score}/10 — {label}\n\n"
        f"Reasoning: {reasoning}\n\n"
        f"{'⚠️ Low BRD alignment. Consider revising the task scope or linking it to a specific BRD goal.' if score < 5 else '✅ This task is well-aligned with the project business requirements.'}"
    )

    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{issue_key}/comment"
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": comment_text}]
                }
            ]
        }
    }

    resp = requests.post(
        url,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
        json=payload
    )

    if resp.status_code == 201:
        print(f"  💬  BRD comment → {issue_key} (Score: {score}/10)")
    else:
        print(f"  ❌  Comment FAILED → {issue_key}: HTTP {resp.status_code}")


def run_brd_alignment(df, brd_path: str = "brd_document.md"):
    """
    Calculates a BRD alignment score for every task in the DataFrame.
    Adds 'brd_score' and 'brd_reasoning' columns.
    Automatically posts a Jira comment for tasks scoring below 5.
    """
    brd_text = load_brd_document(brd_path)

    print("\n📋  BRD Alignment Scoring started...\n")

    scores, reasonings = [], []

    for _, row in df.iterrows():
        issue_key   = row.get("key", "")
        summary     = row.get("summary", "")
        description = row.get("description", "")
        issue_type  = row.get("issue_type", "")

        if issue_type in ["Epik", "Epic"]:
            scores.append(None)
            reasonings.append("Epic — not scored individually.")
            continue

        result    = call_openai_for_brd_score(summary, description, brd_text)
        score     = result["score"]
        reasoning = result["reasoning"]

        scores.append(score)
        reasonings.append(reasoning)

        flag = "🟢" if score >= 7 else ("🟡" if score >= 5 else "🔴")
        print(f"  {flag}  {issue_key}: {score}/10 — {reasoning[:70]}...")

        if 0 < score < 5:
            add_brd_comment_to_jira(issue_key, score, reasoning)

    df["brd_score"]     = scores
    df["brd_reasoning"] = reasonings
    return df


# ══════════════════════════════════════════════════════════════════════════
# 3. GAP DETECTION — BRD goals with no matching Jira task
# ══════════════════════════════════════════════════════════════════════════

def run_gap_detection(df, brd_path: str = "brd_document.md") -> list[dict]:
    """
    Scans every goal in the BRD and compares it against Jira tasks.
    Returns a list of goals that have no corresponding task in Jira.

    Returns: [{"goal_id": str, "goal_title": str, "missing_tasks": str}]
    """
    brd_text = load_brd_document(brd_path)
    goals    = extract_brd_goals(brd_text)

    if not goals:
        print("⚠️  No GOAL-XX headings found in the BRD document.")
        return []

    # Combine all task summaries + descriptions into one searchable string
    jira_corpus = " | ".join(
        f"{row.get('summary','')} {row.get('description','')}"
        for _, row in df.iterrows()
        if row.get("issue_type", "") not in ["Epik", "Epic"]
    ).lower()

    print(f"\n🔍  GAP Detection started... ({len(goals)} BRD goals to scan)\n")

    gaps = []

    for goal in goals:
        prompt = f"""You are a Business Analyst checking if a Jira project covers a specific business goal.

BRD Goal:
ID: {goal['id']}
Title: {goal['title']}
Description: {goal['description']}

Jira tasks (summary + description combined):
{jira_corpus[:12000]}

Question: Does the Jira project have at least one task that addresses this BRD goal?

Respond ONLY in this exact format:
COVERED: yes/no
MISSING_TASKS: <If no, describe in 1 sentence what specific task(s) are missing. If yes, write "All covered.">"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.1
            )
            text = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"  ❌  OpenAI error for {goal['id']}: {e}")
            continue

        covered      = True
        missing_desc = "All covered."
        for line in text.splitlines():
            if line.startswith("COVERED:"):
                covered = "yes" in line.lower()
            elif line.startswith("MISSING_TASKS:"):
                missing_desc = line.replace("MISSING_TASKS:", "").strip()

        status = "✅" if covered else "🚨"
        print(f"  {status}  {goal['id']} — {goal['title'][:50]}")
        if not covered:
            print(f"       Missing: {missing_desc}")
            gaps.append({
                "goal_id":      goal["id"],
                "goal_title":   goal["title"],
                "missing_tasks": missing_desc
            })

    print(f"\n{'─'*55}")
    print(f"  GAP DETECTION RESULT: {len(gaps)} uncovered goal(s) found.")
    print(f"{'─'*55}\n")

    return gaps


def print_gap_report(gaps: list[dict]):
    """Prints the gap detection results in a readable format."""
    if not gaps:
        print("✅  All BRD goals are covered in Jira!")
        return

    print("\n🚨  MISSING COVERAGE — BRD Goals Without Jira Tasks:\n")
    for g in gaps:
        print(f"  [{g['goal_id']}] {g['goal_title']}")
        print(f"  → Missing: {g['missing_tasks']}")
        print()