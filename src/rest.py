from fastapi import FastAPI
import database as db
import parsing_products
import qr
from rest_models import *
import mail_verific
import tokens
import bcrypt

from scheduler import start_scheduler

app = FastAPI()
start_scheduler()

# Создание кода подтверждения
@app.get("/verification-code")
def verification_code(email: str):
    return {"message": mail_verific.send_code(email)}


# Подтверждение кода
@app.post("/verification-code")
def verify(verif: CodeVerification):
    if mail_verific.verify(verif.email, verif.code):
        return {
            "message": "ok",
            "token": tokens.generate({"email": verif.email}, {"hours": 6.0})
        }
    return {"message": "invalid"}


# Логин
@app.post("/login")
def login(login_form: Login):
    user = db.find_by_email(login_form.email)
    if user and bcrypt.checkpw(login_form.password.encode("utf-8"), user['passhash']):
        return {
            "message": "ok",
            "token": tokens.generate({"user_id": user["id"]}, {"days": 90.0})
        }
    return {"message": "incorrect"}


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
        "message": "ok",
        "user": {"name": user["name"], "email": user["email"]},
    }


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
        "message": "ok",
        "token": tokens.generate({"user_id": user_id}, {"days": 90.0})
    }


# Изменение данных пользователя: например, сменить имя, пароль или почту
@app.put("/users/name")
def update_user(user: NewUsername):
    payload = tokens.verify(user.token)
    if not payload or not payload.get("user_id", None):
        return {"message": "bad token"}
    
    return {"message":  db.update_user(payload["user_id"], {"user_name": user.name})}

@app.put("/users/password")
def update_user(user: NewPassword):
    payload = tokens.verify(user.token)
    if not payload or not payload.get("email", None):
        return {"message": "bad token"}
    
    userdb = db.find_by_email(payload["email"])
    if not userdb:
        return {"message": "no user with this email"}
    return {
        "message": db.update_user(
            userdb["id"],
            {"password": bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt())}
        )
    }

@app.put("/users/email")
def update_user(user: NewEmail):
    userpayload = tokens.verify(user.user_token)
    emailpayload = tokens.verify(user.email_token)
    if not userpayload or not userpayload.get("user_id", None):
        return {"message": "bad user token"}
    if not emailpayload or not emailpayload.get("email", None):
        return {"message": "bad email token"}

    return {"message":  db.update_user(userpayload["user_id"], {"email": emailpayload["email"]})}


# Список продуктов данного пользователя
@app.get("/items")
def get_items(token: str):
    payload = tokens.verify(token)
    if not payload or not payload.get("user_id", None):
        return {"message": "bad token"}

    return {
        "message": "ok",
        "items": db.get_items(payload["user_id"])
    }


# Добавить продукты этого пользователя
@app.post("/items")
def add_items(newitems: NewItems):
    payload = tokens.verify(newitems.token)
    if not payload or not payload.get("user_id", None):
         return {"message": "bad token"}
    
    db.add_items(payload["user_id"], newitems.items)
    return {"message": "ok"}


# Сканировать QR-код этого пользователя
@app.post("/qr-text")
def scan_qrtext(qrdata: QRText):
    payload = tokens.verify(qrdata.token)
    if not payload or not payload.get("user_id", None):
         return {"message": "bad token"}
    
    res = qr.parse(qrdata.qrraw)
    if res["ok"]:
        db_res = db.add_qr(payload["user_id"], qrdata.qrraw, res["fp"])

        return {
            "message": "ok",
            "db_response": db_res,
            "items": parsing_products.extract_unit(res["items"]),
        }
    else:
        return {"message": res["errorname"]}


# Достать историю покупок
@app.get("/purchases")
def get_qrs(token: str):
    payload = tokens.verify(token)
    if not payload or not payload.get("user_id", None):
        return {"message": "bad token"}
    
    return {
        "message": "ok",
        "purchases": db.get_qrs(payload["user_id"])
    }


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

# Пуш-токены
@app.post("/notifications/tokens")
def notification_tokens(tokens_N: NotificationTokens):
    payload = tokens.verify(tokens_N.token)
    if not payload or not payload.get("user_id", None):
        return {"message":"bad token"}
    
    user_id = payload["user_id"]

    res = db.save_user_notification_tokens(
        user_id = user_id,
        web_token = tokens_N.web_token,
        tel_token = tokens_N.tel_token,
        email_notification= tokens_N.email_notification
    )
    return {"message":res}