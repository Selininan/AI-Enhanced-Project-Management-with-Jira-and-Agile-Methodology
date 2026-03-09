import requests
from requests.auth import HTTPBasicAuth
import json

email = "EMAILINIZ"
api_token = "TOKENINIZ"
domain = "SIRKETADINIZ.atlassian.net"
email = "zeynepuz2003@gmail.com"
api_token = "ATATT3xFfGF0_rXI42h92VOMVsKnpTWRmVjkqzi8GFUf5qi7Z2E_RgkWkXs2LvbIpO82JJc7VUltJdQKZZWiDSmvQh2uT6EZwAVZ6clxZUM9F9R-k9i0vRi7njrAQntwPYpKm_OCxpBxteYe9NDKZVz_Z8AgQ86DDBPQx4Vg6n9n4-V9gCLeOCk=D3FAC25A"
domain = "zeynepuz200345.atlassian.net"

url = f"https://{domain}/rest/api/3/search"
url = f"https://{domain}/rest/api/3/search/jql"

auth = HTTPBasicAuth(email, api_token)

headers = {
  "Accept": "application/json"
}

query = {
   'jql': 'project = PROJEKODU'
   'jql': 'project = DEV'
}

response = requests.get(
   url,
   headers=headers,
   params=query,
   auth=auth
)

data = response.json()

print(data)

for issue in data["issues"]:
    print(issue["key"], issue["fields"]["summary"])    print(issue)