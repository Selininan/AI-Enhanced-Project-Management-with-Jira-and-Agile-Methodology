"""
jira_support_agent.py
---------------------
AI-powered Jira support chatbot using OpenAI GPT-4o-mini.

Replaces the old keyword-matching system with a real conversational agent.
The agent reads jira_guide.txt as its knowledge base and can also answer
questions about the live Jira project data (sprint health, tasks, capacity).

When MCP is integrated later, replace the df context section with
live MCP tool calls — the OpenAI connection stays exactly the same.

Usage (standalone):
    python agents/jira_support_agent.py

Usage (from main.py):
    from agents.jira_support_agent import JiraSupportAgent
    agent = JiraSupportAgent(df)
    answer = agent.ask("Which tasks are delayed this sprint?")
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE_PATH = os.path.join(BASE_DIR, "jira_guide.txt")


# ══════════════════════════════════════════════════════════════════════════
# 1. LOAD KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════════════════

def load_guide(path: str = GUIDE_PATH) -> str:
    """Reads jira_guide.txt and returns its content."""
    if not os.path.exists(path):
        return "Jira guide not found. Answering from general knowledge only."
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


# ══════════════════════════════════════════════════════════════════════════
# 2. BUILD PROJECT CONTEXT FROM DATAFRAME
# ══════════════════════════════════════════════════════════════════════════

def build_project_context(df) -> str:
    """
    Converts the Jira DataFrame into a compact text summary for the AI.
    When MCP is ready, this will be replaced by live MCP tool calls.
    """
    if df is None or df.empty:
        return "No project data available."

    total       = len(df)
    done        = len(df[df["status"].isin(["Tamam", "Done", "Tamamlandı"])])
    in_progress = len(df[df["status"].isin(["Devam Ediyor", "In Progress"])])
    todo        = len(df[df["status"].isin(["Yapılacaklar", "To Do"])])
    delayed     = len(df[df.get("delay", False) == True]) if "delay" in df.columns else 0
    high_risk   = len(df[df["risk_score"] >= 2.5]) if "risk_score" in df.columns else 0
    total_sp    = int(df["story_points"].sum()) if "story_points" in df.columns else 0

    # Sprint breakdown
    sprint_info = ""
    if "sprint_name" in df.columns:
        for sprint, group in df.groupby("sprint_name"):
            if not sprint:
                continue
            sp = int(group["story_points"].sum()) if "story_points" in group.columns else 0
            sprint_info += f"\n  - {sprint}: {len(group)} tasks, {sp} story points"

    # High risk tasks
    risk_lines = ""
    if "risk_score" in df.columns:
        risky = df[df["risk_score"] >= 2.5][["key", "summary", "risk_score", "assignee"]].head(5)
        for _, r in risky.iterrows():
            risk_lines += f"\n  - {r['key']}: {r['summary'][:50]} (risk: {r['risk_score']}, assignee: {r['assignee']})"

    # Delayed tasks
    delay_lines = ""
    if "delay" in df.columns:
        delayed_tasks = df[df["delay"] == True][["key", "summary", "assignee"]].head(5)
        for _, r in delayed_tasks.iterrows():
            delay_lines += f"\n  - {r['key']}: {r['summary'][:50]} (assignee: {r['assignee']})"

    # Assignee workload
    workload = ""
    if "assignee" in df.columns and "story_points" in df.columns:
        for assignee, group in df.groupby("assignee"):
            sp = int(group["story_points"].sum())
            workload += f"\n  - {assignee}: {len(group)} tasks, {sp} SP"

    context = f"""
=== LIVE PROJECT DATA (BAI Project) ===

Overview:
  Total tasks     : {total}
  Done            : {done}
  In Progress     : {in_progress}
  To Do           : {todo}
  Delayed         : {delayed}
  High Risk       : {high_risk}
  Total Story Pts : {total_sp}

Sprints:{sprint_info if sprint_info else " No sprint data."}

High Risk Tasks:{risk_lines if risk_lines else " None."}

Delayed Tasks:{delay_lines if delay_lines else " None."}

Team Workload:{workload if workload else " No workload data."}
"""
    return context.strip()


# ══════════════════════════════════════════════════════════════════════════
# 3. AGENT CLASS
# ══════════════════════════════════════════════════════════════════════════

class JiraSupportAgent:
    """
    Conversational Jira support agent powered by OpenAI GPT-4o-mini.

    Remembers conversation history within a session (multi-turn).
    Answers both general Jira questions (from the guide) and
    project-specific questions (from live Jira data).
    """

    def __init__(self, df=None):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY not found in environment. "
                "Add it to your .env file."
            )

        self.client          = OpenAI(api_key=api_key)
        self.guide_text      = load_guide()
        self.project_context = build_project_context(df)
        self.history         = []  # conversation history for multi-turn

        # System prompt — stays in every request
        self.system_prompt = f"""You are an AI-powered Jira Support Agent for the BAI project at Beko.
You have two knowledge sources:

1. JIRA GUIDE — General Jira knowledge (how-to, definitions, best practices):
{self.guide_text[:3000]}

2. LIVE PROJECT DATA — Current state of the BAI Jira project:
{self.project_context}

Your rules:
- Answer clearly and concisely in English.
- For general Jira questions (what is an Epic, how to create a task, etc.), use the Jira Guide.
- For project-specific questions (delayed tasks, team workload, sprint status, risk), use the Live Project Data.
- If you don't know something, say so honestly — never make up task names or numbers.
- When listing tasks, include the task key (e.g. BAI-21) and a brief summary.
- Keep answers focused: 3-5 sentences for simple questions, bullet points for lists.
- When MCP is integrated, you will receive even richer real-time data — for now use what's provided."""

    def ask(self, question: str) -> str:
        """
        Sends a question to the agent and returns the answer.
        Conversation history is preserved for follow-up questions.
        """
        self.history.append({"role": "user", "content": question})

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.history
                ],
                max_tokens=500,
                temperature=0.3
            )
            answer = response.choices[0].message.content.strip()

        except Exception as e:
            answer = f"OpenAI API error: {e}"

        self.history.append({"role": "assistant", "content": answer})
        return answer

    def reset(self):
        """Clears conversation history to start a fresh session."""
        self.history = []
        print("🔄  Conversation history cleared.")


# ══════════════════════════════════════════════════════════════════════════
# 4. STANDALONE CHAT MODE
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import pandas as pd

    # Try to load project data if CSV exists
    csv_path = os.path.join(BASE_DIR, "jira_live_dataset.csv")
    df = pd.read_csv(csv_path) if os.path.exists(csv_path) else None

    agent = JiraSupportAgent(df)

    print("\n" + "═" * 55)
    print("  🤖  Jira Support Agent — powered by GPT-4o-mini")
    print("  Type 'quit' to exit | 'reset' to clear history")
    print("═" * 55 + "\n")

    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye! 👋")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye! 👋")
            break
        if question.lower() == "reset":
            agent.reset()
            continue

        print(f"\nAgent: {agent.ask(question)}\n")
