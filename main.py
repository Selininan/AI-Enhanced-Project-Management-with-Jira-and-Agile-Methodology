import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
import matplotlib.pyplot as plt

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

    print(issue_key, response.status_code, response.text)

from agents.risk_agent import calculate_risk
from agents.capacity_agent import capacity_analysis
from agents.recommendation_agent import ai_recommendation
from agents.requirement_agent import requirement_analysis
from agents.task_validation_agent import validate_task
from agents.jira_support_agent import jira_support_answer

email = "zeynepuz2003@gmail.com"
api_token = "ATATT3xFfGF0TPa2jkYWlFSXnAhwlY0acmWFlW8Ri9p0qeFHXAclcY442pSN8IqqXZOisLemj2g--mGEISxL7dKmE-YWtUpcHzHpFYOHkDyeQO3-zKBRRjI1Dyx_Bs--uR5Rp4qzlMhf5m_1lHLE5XejwHExbjQITImqVbZgfg7achxFeqlzUrU=0D32B338"
domain = "zeynepuz200345.atlassian.net"


url = f"https://{domain}/rest/api/3/search/jql"

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

payload = {
   "jql": "project = 'DT' ORDER BY created DESC",
   #bi önceki buydu değiştirdim projeyi almak için "jql": "project = DT ORDER BY assignee, created DESC'"
    "maxResults": 50,
   "fields": [
        "summary", "description", "status", "issuetype", "priority", 
        "assignee", "created", "updated", "parent", "timeoriginalestimate", 
        "timespent", "customfield_10016",
        "customfield_10073" , "customfield_10016"
       
    ]
}

# ... (Yukarıdaki url, headers ve payload kısımları aynı kalacak)

response = requests.post(
    url,
    headers=headers,
    auth=HTTPBasicAuth(email, api_token),
    json=payload
)

data = response.json()

# SADECE ID'Yİ BULMAK İÇİN (Sonra silebilirsin)
print("\n--- JIRA HAM VERİSİ ---")
print(data.get("issues", [])[0]["fields"])
raise SystemExit # Kodu burada durduralım ki terminal çok karışmasın

# 1. İÇ İÇE LİSTELERİ (MADDE İŞARETLERİNİ) ÇÖZEN YENİ FONKSİYON
def extract_text_from_adf(adf_data):
    if isinstance(adf_data, dict):
        if adf_data.get("type") == "text":
            return adf_data.get("text", "")
        if "content" in adf_data:
            return " ".join(extract_text_from_adf(child) for child in adf_data["content"])
    elif isinstance(adf_data, list):
        return " ".join(extract_text_from_adf(item) for item in adf_data)
    return ""

issues_list = []

for issue in data.get("issues", []):
    fields = issue.get("fields", {})

    # 2. AÇIKLAMA (DESCRIPTION) ÇEKME (Maddeli listeler dahil)
    desc_data = fields.get("description")
    description_text = extract_text_from_adf(desc_data).strip() if desc_data else ""
    
    # 3. ATANAN KİŞİ (ASSIGNEE) KONTROLÜ
    assignee_data = fields.get("assignee")
    assignee_name = assignee_data["displayName"] if assignee_data else "Unassigned"

    # 4. UZMANLIK ALANI ÇEKME (customfield_10073 üzerinden)
    expertise_data = fields.get("customfield_10073") 
    
    if isinstance(expertise_data, dict):
        expertise = expertise_data.get("value", "Belirtilmemiş")
    elif expertise_data:
        expertise = str(expertise_data)
    else:
        expertise = "Belirtilmemiş"

  

    # 5. ZAMAN VE DİĞER VERİLERİ ÇEKME
    estimated_seconds = fields.get("timeoriginalestimate")
    spent_seconds = fields.get("timespent")
    story_points = fields.get("customfield_10016")

    estimated_hours = (estimated_seconds / 3600) if estimated_seconds else 0
    spent_hours = (spent_seconds / 3600) if spent_seconds else 0

    parent_data = fields.get("parent")
    epic_value = parent_data.get("key", "") if isinstance(parent_data, dict) else ""

    # 6. TABLOYA (DATAFRAME) EKLENECEK LİSTEYİ OLUŞTURMA
    issues_list.append({
        "key": issue.get("key", ""),
        "summary": fields.get("summary", ""),
        "description": description_text,       # Artık tertemiz, maddeli listeler dahil
        "status": fields["status"]["name"] if fields.get("status") else "Unknown",
        "issue_type": fields["issuetype"]["name"] if fields.get("issuetype") else "Unknown",
        "priority": fields["priority"]["name"] if fields.get("priority") else "None",
        "assignee": assignee_name,             # Artık isimleri doğru alacak
        "expertise": expertise,                # YENİ SÜTUN: Uzmanlık alanı eklendi!
        "created": fields.get("created", ""),
        "updated": fields.get("updated", ""),
        "epic": epic_value,
        "story_points": story_points if story_points else 0,
        "estimated_hours": estimated_hours,
        "spent_hours": spent_hours
    })

df = pd.DataFrame(issues_list)

if df.empty:
    print("No Jira issues found.")
    raise SystemExit

print("\nDEBUG - ASSIGNEE & EXPERTISE CHECK\n")
print(df[["key", "assignee", "expertise", "status"]])

# ... (Kodun geri kalanı yani df hesaplamaları ve agent çağrıları aynen devam edecek)

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

def predict_delay(estimated_hours):
    return estimated_hours > 6

df["predicted_delay"] = df["estimated_hours"].apply(predict_delay)

df = calculate_risk(df)
df = ai_recommendation(df)
df = requirement_analysis(df)
df = validate_task(df)

team_capacity, total_effort = capacity_analysis(df)

total_risk = df["risk_score"].sum()
average_risk = df["risk_score"].mean()

print("\nTASK TABLE\n")
print(df)

print("\nTotal risk:", total_risk)
print("Average risk:", average_risk)

print("\nCAPACITY REPORT\n")
print("Team capacity:", team_capacity)
print("Total effort:", total_effort)

print("\nJIRA SUPPORT AGENT\n")
print(jira_support_answer("Epic nedir?"))
print(jira_support_answer("Story ile task farkı nedir?"))

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

