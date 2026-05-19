import requests
import json
import os

response = requests.post(
  "http://localhost:1234/api/v1/chat",
  headers={
    "Authorization": f"Bearer {os.environ['LM_API_TOKEN']}",
    "Content-Type": "application/json"
  },
  json={
    "model": "google/gemma-4-e4b",
    "input": "Write a short haiku about sunrise."
  }
)
print(json.dumps(response.json(), indent=2))


