import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
import random
import matplotlib.pyplot as plt

email = "zeynepuz2003@gmail.com"
api_token = "ATATT3xFfGF04CPH54bMXpgM5Tc3BaM6YPqQvxvt6kbDL6UHPt1UCCnbVvDh1Zc5e-7S74aVbvd6SGgyhRyoE_mnltjGKgME4V3KCPsILOn_Rm5rR_nFJQ_zzi2LDz4IdI6mWk2VTWDinQFKLlKWGxqmD1r1HCCYye61kAH312UeUKyA66Px3fg=93C5DF95"
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