from fastapi import FastAPI
from pydantic import BaseModel
import database as db
import qr

class QRText(BaseModel):
    qrraw: str

app = FastAPI()

# возвращает список ВСЕХ позиций, хранящихся в БД
# возвращает список СТРОК - названий товаров
@app.get("/items")
async def pull_items():
    items = []
    for item in db.pull_products():
        items += [item.name]
    return items


# прогон расшифровки QR-кода через API для получения списка товаров
# добавляем эти товары в БД + возвращаем прочитанный список на фронт
@app.post("/items")
async def pass_qrcode_text(qrcode_text: QRText):
    return qr.get_item_names_by_qrraw(qrcode_text.qrraw)
