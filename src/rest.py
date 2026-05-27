from fastapi import FastAPI
import database as db
import parsing_products
import qr
from rest_models import *
import mail_verific
import tokens
import bcrypt

app = FastAPI()


# Создание нового пользователя
@app.post("/users")
def new_user(user: NewUser):
    payload = tokens.verify(user.token)
    if not payload or not payload.get("email", None):
        return {"message": "bad token"}

    user_id = db.create_user(user.name, payload["email"], bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()))
    if not user_id:
        return {"message": "error"}
    elif user_id == "exists":
        return {"message": "email exists"}
    
    return {
        "message": "success",
        "token": tokens.generate({"user_id": user_id}, {"days": 90.0})
    }


# Создание кода подтверждения
@app.get("/verification-code")
def verification_code(email: str):
    return {"message": mail_verific.send_code(email)}


# Подтверждение кода
@app.post("/verification-code")
def verify(verif: CodeVerification):
    if mail_verific.verify(verif.email, verif.code):
        return {
            "message": "success",
            "token": tokens.generate({"email": verif.email}, {"hours": 6.0})
        }
    return {"message": "invalid"}


# Поиск пользователя по токену
@app.get("/users")
def get_user(token: str):
    payload = tokens.verify(token)
    if not payload or not payload.get("user_id", None):
        return {"message": "bad token"}

    user = db.get_user(payload["user_id"])
    if not user:
        return {"message": "user not found"}
    return {
        "message": "success",
        "user": {"name": user["name"], "email": user["email"]},
    }


# Логин
@app.post("/login")
def login(login_form: Login):
    user = db.find_by_email(login_form.email)
    if user and bcrypt.checkpw(login_form.password.encode("utf-8"), user['passhash']):
        return {
            "message": "success",
            "token": tokens.generate({"user_id": user["id"]}, {"days": 90.0})
        }
    return {"message": "incorrect"}


# Список продуктов данного пользователя
@app.get("/items")
def get_items(token: str):
    payload = tokens.verify(token)
    if not payload or not payload.get("user_id", None):
        return {"message": "bad token"}

    return {
        "message": "success",
        "items": db.get_items(payload["user_id"])
    }


# Добавить продукты этого пользователя
@app.post("/items")
def add_items(newitems: NewItems):
    payload = tokens.verify(newitems.token)
    if not payload or not payload.get("user_id", None):
         return {"message": "bad token"}
    
    db.add_items(payload["user_id"], newitems.items)
    return {"message": "success"}


# Сканировать QR-код этого пользователя
@app.post("/qr-text")
def scan_qrtext(qrdata: QRText):
    payload = tokens.verify(qrdata.token)
    if not payload or not payload.get("user_id", None):
         return {"message": "bad token"}
    
    res = qr.get_items_by_qrraw(qrdata.qrraw)
    if res["successful"]:
        return {
            "message": "success",
            "items": parsing_products.extract_unit(res["items"]),
        }
    else:
        return {"message": res["errorname"]}


# Удалить указанные продукты
@app.post("/items/delete")
def delete_items(dropitems: DropItems):
    payload = tokens.verify(dropitems.token)
    if not payload or not payload.get("user_id", None):
         return {"message": "bad token"}
    
    return {"message": db.items_to_delete(payload["user_id"],dropitems.item_ids)}


# Обновление данных продуктов
@app.put("/items")
def update(upditems:UPDItems):
    payload = tokens.verify(upditems.token)
    if not payload or not payload.get("user_id", None):
         return {"message": "bad token"}
    
    return {"message": db.update_items(payload["user_id"], upditems.items_upd)}
