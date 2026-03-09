import requests
from requests.auth import HTTPBasicAuth
import json

email = "EMAILINIZ"
api_token = "TOKENINIZ"
domain = "SIRKETADINIZ.atlassian.net"

url = f"https://{domain}/rest/api/3/search"

auth = HTTPBasicAuth(email, api_token)

headers = {
  "Accept": "application/json"
}

query = {
   'jql': 'project = PROJEKODU'
}

response = requests.get(
   url,
   headers=headers,
   params=query,
   auth=auth
)

data = response.json()

for issue in data["issues"]:
    print(issue["key"], issue["fields"]["summary"])