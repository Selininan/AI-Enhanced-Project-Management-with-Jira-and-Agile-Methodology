import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
JIRA_EMAIL     = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_DOMAIN    = os.getenv("JIRA_DOMAIN")

# ── BRD Hedefleri (Beko AI Projesi) ─────────────────────────────────────────
# Bu liste projenin BRD dokümanından çıkarılmış temel iş hedeflerini temsil eder.
# Gerçek BRD değişirse bu liste güncellenir.

BRD_GOALS = """
Business Requirements Document (BRD) — Beko AI-Enhanced Jira System

Core Business Goals:
1. Implement secure SSO authentication using Azure AD / OAuth 2.0 for Beko corporate accounts.
2. Build a Role-Based Access Control (RBAC) system with PM, Developer, and Viewer roles.
3. Create an audit log system that tracks user activities for the last 30 days with Excel export.
4. Develop a product catalog and inventory management module for warehouse staff and product managers.
5. Enable product filtering by category and price range with real-time results.
6. Implement automatic critical stock alerts when inventory drops below 10 units.
7. Build AI-powered sprint health analysis with risk scoring and delay detection.
8. Generate capacity reports comparing team workload against available hours before sprint starts.
9. Provide daily automated sprint summaries to Project Managers via Microsoft Teams at 09:00.
10. Integrate all AI agents as HTTP endpoints via FastAPI for n8n and dashboard consumption.
11. Configure n8n to listen to Jira webhook events and trigger AI analysis automatically.
12. Ensure all credentials are stored securely in environment variables, never in source code.
"""


def call_gemini_for_brd_score(task_summary: str, task_description: str) -> dict:
    """
    Google Gemini API'ye task bilgisini gönderir, BRD uyum skoru ve açıklama alır.
    Returns: {"score": int, "reasoning": str}
    """
    prompt = f"""You are a Business Analyst evaluating Jira tasks against a Business Requirements Document (BRD).

{BRD_GOALS}

Task to evaluate:
- Summary: {task_summary}
- Description: {task_description if task_description else "No description provided."}

Instructions:
1. Analyze how well this task contributes to the BRD goals above.
2. Assign a score from 1 to 10 (1 = no alignment, 10 = perfect alignment).
3. Write a short 1-2 sentence reasoning in English explaining the score.

Respond ONLY in this exact format (no extra text):
SCORE: <number>
REASONING: <one or two sentences>"""

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 200}
        }
    )

    if response.status_code != 200:
        try:
            err_detail = response.json()
        except Exception:
            err_detail = response.text
        print(f"[Gemini DEBUG] status={response.status_code} body={err_detail}")
        return {"score": 0, "reasoning": f"Gemini API error: {response.status_code}"}

    text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    score = 0
    reasoning = ""
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
    """Jira issue'ya BRD alignment skoru comment olarak yazar."""
    if score >= 7:
        label = "✅ HIGH ALIGNMENT"
    elif score >= 5:
        label = "⚠️ MEDIUM ALIGNMENT"
    else:
        label = "🚨 LOW ALIGNMENT"

    comment_text = (
        f"🤖 BRD Alignment Analysis\n\n"
        f"Alignment Score: {score}/10 — {label}\n\n"
        f"Reasoning: {reasoning}\n\n"
        f"{'⚠️ This task has low BRD alignment. Consider revising scope or linking to a BRD goal.' if score < 5 else '✅ This task is well-aligned with project business requirements.'}"
    )

    comment_url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{issue_key}/comment"
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

    response = requests.post(
        comment_url,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
        json=payload
    )

    if response.status_code == 201:
        print(f"✅ BRD comment added to {issue_key} (Score: {score}/10)")
    else:
        print(f"❌ Failed to add BRD comment to {issue_key}: {response.status_code}")


def run_brd_alignment(df):
    """
    DataFrame'deki tüm tasklara BRD skoru hesaplar.
    Yeni 'brd_score' ve 'brd_reasoning' kolonları ekler.
    Score < 5 olan taskları Jira'ya comment olarak yazar.
    """
    print("\n📋 BRD Alignment Analysis başlıyor...\n")

    brd_scores = []
    brd_reasonings = []

    for _, row in df.iterrows():
        issue_key   = row.get("key", "")
        summary     = row.get("summary", "")
        description = row.get("description", "")

        # Epic'leri atla, içerik analizi için uygun değil
        if row.get("issue_type", "") in ["Epik", "Epic"]:
            brd_scores.append(None)
            brd_reasonings.append("Epic — not scored individually.")
            continue

        result = call_gemini_for_brd_score(summary, description)
        score     = result["score"]
        reasoning = result["reasoning"]

        brd_scores.append(score)
        brd_reasonings.append(reasoning)

        print(f"{issue_key}: {score}/10 — {reasoning[:60]}...")

        # Score < 5 ise Jira'ya otomatik comment yaz
        if score > 0 and score < 5:
            add_brd_comment_to_jira(issue_key, score, reasoning)

    df["brd_score"]     = brd_scores
    df["brd_reasoning"] = brd_reasonings

    return df