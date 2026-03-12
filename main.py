import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
import random
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import os

email = "zeynepuz2003@gmail.com"
api_token = "ATATT3xFfGF0TPa2jkYWlFSXnAhwlY0acmWFlW8Ri9p0qeFHXAclcY442pSN8IqqXZOisLemj2g--mGEISxL7dKmE-YWtUpcHzHpFYOHkDyeQO3-zKBRRjI1Dyx_Bs--uR5Rp4qzlMhf5m_1lHLE5XejwHExbjQITImqVbZgfg7achxFeqlzUrU=0D32B338"
domain = "zeynepuz200345.atlassian.net"

url = f"https://{domain}/rest/api/3/search/jql"

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

payload = {
    "jql": "assignee = currentUser() ORDER BY created DESC",
    "maxResults": 50,
    "fields": ["summary", "status"]
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
    issues_list.append({
        "key": issue["key"],
        "summary": issue["fields"]["summary"],
        "status": issue["fields"]["status"]["name"],
        "estimated_days": random.randint(1, 10),
        "real_days": random.randint(1, 10)
    })

df = pd.DataFrame(issues_list)

df["delay"] = df["real_days"] > df["estimated_days"]



def predict_delay(estimated):
    if estimated > 5:
        return True
    else:
        return False


df["predicted_delay"] = df["estimated_days"].apply(predict_delay)

def risk_score(row):

    score = 0

    if row["delay"]:
        score += 2

    if row["estimated_days"] > 5:
        score += 1

    if row["status"] != "Done":
        score += 1

    return score

df["risk_score"] = df.apply(risk_score, axis=1)


total_risk = df["risk_score"].sum()

average_risk = df["risk_score"].mean()



print("\nTASK TABLE\n")
print(df)

print("\nTotal risk:", total_risk)
print("Average risk:", average_risk)

plt.figure()
df["risk_score"].plot(kind="bar")

plt.title("Task Risk Scores")
plt.xlabel("Task")
plt.ylabel("Risk")

plt.show()

def ai_recommendation(row):

    if row["risk_score"] >= 3:
        return "High risk → split task or add developer"

    elif row["delay"]:
        return "Delayed → increase priority"

    elif row["status"] != "Done":
        return "In progress → monitor"

    else:
        return "OK"


df["recommendation"] = df.apply(ai_recommendation, axis=1)

print("\nAI RECOMMENDATIONS\n")

print(
    df[
        [
            "key",
            "status",
            "estimated_days",
            "real_days",
            "risk_score",
            "recommendation",
        ]
    ]
)

print("\nSPRINT HEALTH REPORT\n")

if average_risk < 1:
    print("Sprint status: LOW RISK")

elif average_risk < 2:
    print("Sprint status: MEDIUM RISK")

else:
    print("Sprint status: HIGH RISK")


delayed_tasks = df[df["delay"] == True]

print("\nDelayed tasks:", len(delayed_tasks))

high_risk_tasks = df[df["risk_score"] >= 3]

print("High risk tasks:", len(high_risk_tasks))


if len(high_risk_tasks) > 2:
    print("Recommendation: Add more developers to sprint")

if len(delayed_tasks) > 2:
    print("Recommendation: Review planning accuracy")

if average_risk > 2:
    print("Recommendation: Reduce sprint workload")