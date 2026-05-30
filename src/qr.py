import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
api_url = os.getenv("API_URL")

# Ошибки, возвращаемые с API proverkacheka.com
# "неопределенная ошибка" - остальные случаи
error_dict = {
    0: "чек некорректен",
    1: "успешно",
    2: "данные чека пока не получены",
    3: "превышено кол-во запросов",
    4: "ожидание перед повторным запросом",
}
error_oth = "неопределенная ошибка"


def parse(qrraw: str) -> dict:
    rbody = {"token": api_key, "qrraw": qrraw}
    
    try:
        r = requests.post(api_url, data=rbody).json()
    except Exception:
        return {"ok": False, "errorname": "ошибка сети или не верный JSON"}
    
    code = r.get("code")
    if code != 1:
        error_text = error_dict.get(code, error_oth)
        return {"ok": False, "errorname": error_text}

    items = []
    raw_items = r.get("data", {}).get("json", {}).get("items", [])
    for item in raw_items:
        items.append(
            {
                "name": item.get("name", "Неопознанный товар"),
                "quantity": item.get("quantity", 1.0),
                "price": item.get("price", 0) / 100.0
            }
        )
    return {"ok": True, "items": items, "fp": r["data"]["json"]["fiscalSign"], "data": r["data"]["json"]}
