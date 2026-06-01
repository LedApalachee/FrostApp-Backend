from fastapi import FastAPI
import database as db
import parsing_products
import qr
from rest_models import *
import mail_verific
import tokens
import bcrypt
import json
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

@app.put("/users/password/authorized")
def update_user(user: NewPassword):
    payload = tokens.verify(user.token)
    if not payload or not payload.get("user_id", None):
        return {"message": "bad token"}
    
    userdb = db.get_user(payload["user_id"])
    if not userdb:
        return {"message": "user not found"}
    return {
        "message": db.update_user(
            userdb["id"],
            {"password": bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt())}
        )
    }

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


# Удалить указанные продукты
@app.put("/items/delete")
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


# Получить заголовки всех рецептов
@app.get("/recipes/general")
def get_recipe_headers(token: str):
    payload = tokens.verify(token)
    if not payload or not payload.get("user_id", None):
        return {"message": "bad token"}
    
    recipes = db.get_recipes()
    result = []
    for recipe in recipes:
        result.append({
            "id": recipe["id"],
            "name": recipe["name"],
            "description": recipe["description"],
            "icon": recipe["icon"]
        })
    
    return {"message": "ok", "recipes": result}


# Получить конкретный рецепт
@app.get("/recipes/specific")
def get_specific_recipe(token: str, recipe_id: int):
    payload = tokens.verify(token)
    if not payload or not payload.get("user_id", None):
        return {"message": "bad token"}

    recipe = db.get_recipe(recipe_id)
    if not recipe:
        return {"message": "recipe not found"}
    
    try:
        ingredients = json.loads(recipe["ingredients_json"])
    except:
        ingredients = None
    recipe.pop("ingredients_json")
    recipe.update({"ingredients": ingredients})
    
    return {"message": "ok", "recipe": recipe}


# Получить все рецепты
@app.get("/recipes")
def get_recipes(token: str):
    payload = tokens.verify(token)
    if not payload or not payload.get("user_id", None):
        return {"message": "bad token"}

    user_items = db.get_items(payload["user_id"])
    user_categories = set()
    for item in user_items:
        if item.get("category", None):
            user_categories.add(item["category"])

    recipes = db.get_recipes()
    result = []
    for r in recipes:
        try:
            ingredients = json.loads(r["ingredients_json"])
        except:
            ingredients = None
        r.pop("ingredients_json")
        matched = 0
        total = 0
        missing = []
        ingredients_list = [] if ingredients == None else ingredients
        for ing in ingredients_list:
            if ing.get("optional", None):
                continue
            total += 1
            ing_name_lower = ing["name"].lower()
            ing_cat_lower = ing["category"].lower()
            found = False
            for item in user_items:
                if item["name"].lower() == ing_name_lower and not item["deleted"]:
                    found = True
                    break
                if item.get("category", None) and item["category"].lower() == ing_cat_lower and not item["deleted"]:
                    found = True
                    break
            if found:
                matched += 1
            else:
                missing.append(ing["name"])

        match_percent = int((matched / total * 100)) if total > 0 else 0
        r["match_percent"] = match_percent
        r["missing_ingredients"] = missing
        r["ingredients"] = ingredients
        result.append(r)

    result.sort(key=lambda x: x["match_percent"], reverse=True)
    return {"message": "ok", "recipes": result}


# Добавить рецепт
@app.post("/recipes")
def add_recipe(recipe: NewRecipe):
    payload = tokens.verify(recipe.token)
    if not payload or not payload.get("is_dev", None):
        return {"message": "bad token"}
    
    return {"message": db.add_recipe(recipe.name, recipe.description, recipe.icon, recipe.cook_time_minutes, recipe.servings, recipe.ingredients_json, recipe.instructions)}
