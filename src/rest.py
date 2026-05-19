from fastapi import FastAPI, Body
from pydantic import BaseModel
from dotenv import load_dotenv
import database as db
import qr
import jwt
import os


class QRText(BaseModel):
    user_id: int
    qrraw: str
    token: str

class Register(BaseModel):
    name: str
    email: str
    password: str

class Login(BaseModel):
    email: str
    password: str

class NewItems(BaseModel):
    user_id: int
    items: list
    token: str

class DropItems(BaseModel):
    item_ids: list[int]
    user_id: int
    token: str


app = FastAPI()
load_dotenv()


# Регистрация нового пользователя
@app.post("/users")
def new_user(user: Register):
    if db.find_by_email(user.email):
        return {"message": "email exists"}
    user_id = db.create_user(user.name, user.email, user.password)
    return {
        "message": "success",
        "user_id": user_id,
        "token": jwt.encode({"user_id": user_id}, os.getenv("SECRET_KEY"), algorithm="HS256")
    }


@app.get("/users")
def get_user(user_id: int, token: str):
    if token != jwt.encode({"user_id": user_id}, os.getenv("SECRET_KEY"), algorithm="HS256"):
        return {"message": "bad token"}
    user = db.get_user(user_id)
    if not user:
        return {"message": "user not found"}
    return {
        "message": "success",
        "user": {"id": user["id"], "name": user["name"], "email": user["email"]}
    }


# Логин
@app.post("/login")
def login(login_form: Login):
    user = db.find_by_email(login_form.email)
    if user and user["passhash"] == login_form.password:
        return {
            "message": "success",
            "user_id": user["id"],
            "token": jwt.encode({"user_id": user["id"]}, os.getenv("SECRET_KEY"), algorithm="HS256")
        }
    return {"message": "incorrect"}


# Список продуктов данного пользователя
@app.get("/items")
def get_items(user_id: int, token: str):
    if token == jwt.encode({"user_id": user_id}, os.getenv("SECRET_KEY"), algorithm="HS256"):
        return {"items": db.get_items(user_id)}
    return {"message": "bad token"}


# Добавить продукты этого пользователя
@app.post("/items")
def add_items(newitems: NewItems):
    if newitems.token == jwt.encode({"user_id": newitems.user_id}, os.getenv("SECRET_KEY"), algorithm="HS256"):
        db.add_items(newitems.user_id, newitems.items)
        return {"message": "success"}
    return {"message": "bad token"}


# Сканировать QR-код этого пользователя
@app.post("/qr-text")
def scan_qrtext(qrdata: QRText):
    if qrdata.token == jwt.encode({"user_id": qrdata.user_id}, os.getenv("SECRET_KEY"), algorithm="HS256"):
        return qr.get_item_names_by_qrraw(qrdata.qrraw)
    return {"message": "bad token"}


# Удалить данные продукты
@app.post("/items/delete")
def delete_items(dropitems: DropItems):
    if dropitems.token == jwt.encode({"user_id": dropitems.user_id}, os.getenv("SECRET_KEY"), algorithm="HS256"):
        return {"message": db.items_to_delete(dropitems.item_ids)}
    return {"message": "bad token"}
