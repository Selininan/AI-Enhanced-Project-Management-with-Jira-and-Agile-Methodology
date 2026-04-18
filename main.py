import os
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv

from agents.risk_agent import calculate_risk
from agents.capacity_agent import capacity_analysis
from agents.recommendation_agent import ai_recommendation
from agents.requirement_agent import requirement_analysis
from agents.task_validation_agent import validate_task
from agents.jira_support_agent import GUIDE_TEXT, GUIDE_SECTIONS, jira_support_answer
from context.context_builder import build_context
from reports.pdf_report import create_pdf_report

load_dotenv()

# CONFIG
email = os.getenv("JIRA_EMAIL")
api_token = os.getenv("JIRA_API_TOKEN")
domain = os.getenv("JIRA_DOMAIN")
project_key = os.getenv("JIRA_PROJECT_KEY", "DT")
url = f"https://{domain}/rest/api/3/search/jql"

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}


def add_jira_comment(issue_key, comment_text):
    comment_url = f"https://{domain}/rest/api/3/issue/{issue_key}/comment"

    comment_payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": comment_text
                        }
                    ]
                }
            ]
        }
    }

    response = requests.post(
        comment_url,
        headers=headers,
        auth=HTTPBasicAuth(email, api_token),
        json=comment_payload
    )

    if response.status_code == 201:
        print(f"Comment added to {issue_key}")
    else:
        print(f"Failed to add comment to {issue_key}: {response.status_code}")


def extract_text_from_adf(adf_data):
    if isinstance(adf_data, dict):
        if adf_data.get("type") == "text":
            return adf_data.get("text", "")
        if "content" in adf_data:
            return " ".join(extract_text_from_adf(child) for child in adf_data["content"])
    elif isinstance(adf_data, list):
        return " ".join(extract_text_from_adf(item) for item in adf_data)
    return ""


def predict_delay(estimated_hours):
    return estimated_hours > 6


def fetch_and_analyze():
    payload = {
        "jql": f"project = '{project_key}' ORDER BY created DESC",
        "maxResults": 50,
        "fields": [
            "summary",
            "description",
            "status",
            "issuetype",
            "priority",
            "assignee",
            "created",
            "updated",
            "parent",
            "timeoriginalestimate",
            "timespent",
            "customfield_10016",   # story points
            "customfield_10073"    # expertise
        ]
    }

    response = requests.post(
        url,
        headers=headers,
        auth=HTTPBasicAuth(email, api_token),
        json=payload
    )

    data = response.json()

    issues_list = []

    for issue in data.get("issues", []):
        fields = issue.get("fields", {})

        desc_data = fields.get("description")
        description_text = extract_text_from_adf(desc_data).strip() if desc_data else ""

        assignee_data = fields.get("assignee")
        assignee_name = assignee_data["displayName"] if assignee_data else "Unassigned"

        expertise_data = fields.get("customfield_10073")
        if isinstance(expertise_data, dict):
            expertise = expertise_data.get("value", "Belirtilmemiş")
        elif expertise_data:
            expertise = str(expertise_data)
        else:
            expertise = "Belirtilmemiş"

        estimated_seconds = fields.get("timeoriginalestimate")
        spent_seconds = fields.get("timespent")
        story_points = fields.get("customfield_10016")

        estimated_hours = (estimated_seconds / 3600) if estimated_seconds else 0
        spent_hours = (spent_seconds / 3600) if spent_seconds else 0

        parent_data = fields.get("parent")
        epic_value = parent_data.get("key", "") if isinstance(parent_data, dict) else ""

        issues_list.append({
            "key": issue.get("key", ""),
            "summary": fields.get("summary", ""),
            "description": description_text,
            "status": fields["status"]["name"] if fields.get("status") else "Unknown",
            "issue_type": fields["issuetype"]["name"] if fields.get("issuetype") else "Unknown",
            "priority": fields["priority"]["name"] if fields.get("priority") else "None",
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
        print("No JIRA issues found.")
        return

    print("\nDEBUG - ASSIGNEE & EXPERTISE CHECK\n")
    print(df[["key", "assignee", "expertise", "status"]])

    # Time tracking yoksa story point'ten estimate üret
    df["estimated_hours"] = df.apply(
        lambda row: row["estimated_hours"] if row["estimated_hours"] > 0 else row["story_points"] * 2,
        axis=1
    )

    # Time spent yoksa geçici simülasyon
    df["spent_hours"] = df.apply(
        lambda row: row["spent_hours"] if row["spent_hours"] > 0 else max(row["estimated_hours"] - 1, 0),
        axis=1
    )

    df["delay"] = df["spent_hours"] > df["estimated_hours"]
    df["predicted_delay"] = df["estimated_hours"].apply(predict_delay)

    df = calculate_risk(df)
    df = ai_recommendation(df)
    df = requirement_analysis(df)
    df = validate_task(df)

    team_capacity, total_effort, bottleneck_report = capacity_analysis(df)

    total_risk = df["risk_score"].sum()
    average_risk = df["risk_score"].mean()

    print("\nTASK TABLE\n")
    print(df)

    print("\nTotal risk:", total_risk)
    print("Average risk:", average_risk)

    print("\nCAPACITY REPORT\n")
    print(f"Genel Takım Kapasitesi: {team_capacity} Saat")
    print(f"Sprintteki Toplam İş Yükü: {total_effort} Saat")
    print("-" * 30)
    for report in bottleneck_report:
        print(report)
    print("-" * 30)

    if total_effort > team_capacity:
        print("Sprint overloaded")
    else:
        print("Sprint feasible")

    print("\nAI RECOMMENDATIONS\n")
    print(df[
        [
            "key",
            "status",
            "issue_type",
            "priority",
            "story_points",
            "estimated_hours",
            "spent_hours",
            "risk_score",
            "recommendation",
            "requirement_alignment",
            "validation_result"
        ]
    ])

    print("\nVALIDATION REPORT\n")
    print(df[["key", "summary", "validation_result"]])

    print("\nVALIDATION SUMMARY\n")
    print(df["validation_result"].value_counts())

    # Sprint sağlık raporu
    context = build_context(df)
    print("\nSPRINT HEALTH REPORT\n")

    if average_risk < 1:
        print("Sprint status: LOW RISK")
    elif average_risk < 2:
        print("Sprint status: MEDIUM RISK")
    else:
        print("Sprint status: HIGH RISK")

    delayed_tasks = df[df["delay"] == True]
    high_risk_tasks = df[df["risk_score"] >= 3]

    print("Delayed tasks:", len(delayed_tasks))
    print("High risk tasks:", len(high_risk_tasks))

    if len(high_risk_tasks) > 2:
        print("Recommendation: Add more developers to sprint")

    if len(delayed_tasks) > 2:
        print("Recommendation: Review planning accuracy")

    if average_risk > 2:
        print("Recommendation: Reduce sprint workload")

    df.to_csv("jira_dataset.csv", index=False)
    print("\nDataset saved as jira_dataset.csv")

    df[["key", "summary", "validation_result"]].to_csv("validation_report.csv", index=False)
    print("Validation report saved as validation_report.csv")

    plt.figure(figsize=(10, 5))
    df.set_index("key")["risk_score"].plot(kind="bar", color="skyblue")
    plt.title("Task Risk Scores")
    plt.xlabel("Task")
    plt.ylabel("Risk Score")
    plt.tight_layout()
    plt.savefig("risk_chart.png")
    print("Risk chart saved as risk_chart.png")

    # PDF raporu oluştur
    create_pdf_report(df, total_effort, team_capacity)

    print("\nWRITING COMMENTS TO JIRA\n")

    problem_tasks = df[
        (df["validation_result"] != "Valid") | (df["risk_score"] >= 3)
    ]

    for _, row in problem_tasks.iterrows():
        comment = (
            f"🤖 AI Sprint Analysis\n\n"
            f"• Risk Score: {row['risk_score']}\n"
            f"• Status: {row['status']}\n\n"
            f"⚠️ Issues:\n{row['validation_result']}\n\n"
            f"💡 Recommendation:\n{row['recommendation']}"
        )
        add_jira_comment(row["key"], comment)

    print("\nJIRA SUPPORT AGENT\n")
    print("-" * 40)
    print(jira_support_answer("What is the difference between a story and a task?"))
    print("-" * 40)
    print(jira_support_answer("Why is this task invalid?"))
    print("-" * 40)
    print(jira_support_answer("Who actually uses Jira in our company?"))
    print("-" * 40)
    print(jira_support_answer("How can I share my plan with the stakeholders?"))
    print("-" * 40)
    print(jira_support_answer("What if I want to plan for different worst-case scenarios?"))
    print("-" * 40)
    print(jira_support_answer("How do I track the progress of my team?"))
    print("-" * 40)


if __name__ == "__main__":
    fetch_and_analyze()
