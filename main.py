import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
import random
import matplotlib.pyplot as plt



from agents.risk_agent import calculate_risk
from agents.capacity_agent import capacity_analysis
from agents.recommendation_agent import ai_recommendation
from agents.requirement_agent import requirement_analysis
from context.context_builder import build_context
from reports.pdf_report import create_pdf_report

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


# delay hesaplama
df["delay"] = df["real_days"] > df["estimated_days"]

# 🤖 AGENTS ÇALIŞIYOR
df = calculate_risk(df)

df = ai_recommendation(df)

df = requirement_analysis(df)

team_capacity, total_effort = capacity_analysis(df)

print("\nTASK TABLE\n")
print(df)

print("\nTEAM CAPACITY:", team_capacity)
print("TOTAL EFFORT:", total_effort)

project_context = build_context(df)

print("\nPROJECT CONTEXT\n")

for key,value in project_context.items():
    print(key, ":", value)
    
    
# grafik
plt.figure()
df["risk_score"].plot(kind="bar")

plt.title("Task Risk Scores")
plt.xlabel("Task")
plt.ylabel("Risk")

plt.savefig("risk_chart.png")


create_pdf_report(df, total_effort, team_capacity)



'''çalışıyordu sonrasında folderlara ayırdım.'''

'''df["delay"] = df["real_days"] > df["estimated_days"]



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
plt.ylabel("Risk Score")

plt.savefig("risk_chart.png")



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
    
    
    
    
print("\nVELOCITY REPORT\n")

done_tasks = df[df["status"] == "Tamam"]

velocity = len(done_tasks)

total_tasks = len(df)

print("Total tasks:", total_tasks)
print("Done tasks:", velocity)

if total_tasks > 0:
    velocity_rate = velocity / total_tasks
else:
    velocity_rate = 0

print("Velocity rate:", velocity_rate)


if velocity_rate > 0.7:
    print("Sprint performance: GOOD")

elif velocity_rate > 0.4:
    print("Sprint performance: MEDIUM")

else:
    print("Sprint performance: LOW")    
    
    
    
pdf = FPDF()
pdf.add_page()

pdf.set_font("Arial", size=12)

pdf.cell(200,10,"AI Sprint Report",ln=True)

pdf.cell(200,10,f"Total Tasks: {len(df)}",ln=True)
pdf.cell(200,10,f"Total Risk: {total_risk}",ln=True)
pdf.cell(200,10,f"Average Risk: {average_risk}",ln=True)

pdf.cell(200,10,"",ln=True)
pdf.cell(200,10,"High Risk Tasks:",ln=True)

for index,row in df.iterrows():
    if row["risk_score"] >= 3:
        pdf.cell(200,10,f'{row["key"]} - Risk:{row["risk_score"]}',ln=True)

pdf.cell(200,10,"",ln=True)

pdf.image("risk_chart.png", x=10, y=None, w=180)

pdf.output("sprint_report.pdf")

print("PDF REPORT CREATED")  




print("\nCAPACITY ANALYSIS\n")

team_members = 3
hours_per_member = 40   # haftalık çalışma
sprint_weeks = 2

team_capacity = team_members * hours_per_member * sprint_weeks

print("Team capacity (hours):", team_capacity)


df["effort_hours"] = df["estimated_days"] * 6

total_effort = df["effort_hours"].sum()

print("Total sprint effort:", total_effort)


print("\nSPRINT FEASIBILITY\n")

if total_effort > team_capacity:
    print("Sprint overloaded")
    print("Recommendation: Reduce tasks")

else:
    print("Sprint feasible")'''