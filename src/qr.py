import os
import requests
from dotenv import load_dotenv
import database as db

load_dotenv()
api_key = os.getenv("API_KEY")
api_url = os.getenv("API_URL")

def get_item_names_by_qrraw(qrraw: str) -> list[str]:
    item_names = []
    items_db = []
    rbody = {"token":api_key, "qrraw":qrraw}
    r = requests.post(api_url, data=rbody)
    for item in r.json()['data']['json']['items']:
        # формируем список названий товаров для отправки на фронт
        item_names += [item['name']]
        
        # формируем список товаров для сохранения в БД
        item_db = db.Product()
        item_db.name = item['name']
        items_db += [item_db]

    db.add_product(items_db)
    return item_names
