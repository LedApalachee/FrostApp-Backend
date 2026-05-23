import os
import requests
import database as db
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
api_url = os.getenv("API_URL")

# Во-первых как-будто для чистоты кода, сам словарь ошибок должен быть вне функции
# "неопределенная ошибка" - остальные случаи
error_dict = {
    0: "чек некорректен",
    1: "успешно",
    2: "данные чека пока не получены",
    3: "превышено кол-во запросов",
    4: "ожидание перед повторным запросом",
}
error_oth = "неопределенная ошибка"


def get_items_by_qrraw(qrraw: str) -> dict:
    rbody = {"token": api_key, "qrraw": qrraw}
    # try и catch как будто надо
    try:
        r = requests.post(api_url, data=rbody).json()
    except Exception:
        return {"successful": False, "errorname": "ошибка сети или не верный JSON"}
    # обработка кодов ошибок с API proverkacheka.com
    # errors = ["чек некорректен", "успешно", "данные чека пока не получены", "превышено кол-во запросов", "ожидание перед повторным запросом", "неопределенная ошибка"]
    code = r.get("code")
    if code != 1:
        error_text = error_dict.get(code, error_oth)
        return {"successful": False, "errorname": error_text}

    items = []
    raw_items = r.get("data", {}).get("json", {}).get("items", [])
    for item in raw_items:
        items.append(
            {
                "name": item.get("name", "Неопознанный товар"),
                "quantity": item.get("quantity", 1.0),
            }
        )
    return {"successful": True, "items": items}
