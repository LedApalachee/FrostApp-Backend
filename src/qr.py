import os
import requests
import database as db
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
api_url = os.getenv("API_URL")

def get_item_names_by_qrraw(qrraw: str) -> list[str]:
    item_names = []
    rbody = {"token":api_key, "qrraw":qrraw}
    r = requests.post(api_url, data=rbody)
    for item in r.json()['data']['json']['items']:
        item_names += [item['name']]
    return item_names
