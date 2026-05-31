from fastapi import FastAPI
import database as db
import parsing_products
import qr
from rest_models import *
import mail_verific
import tokens
import bcrypt
import json
import httpx
import os

app = FastAPI()

@app.on_event("startup")
def startup():
    db.seed_recipes_if_empty()


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
    
    res = qr.get_items_by_qrraw(qrdata.qrraw)
    if res["successful"]:
        return {
            "message": "ok",
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


# Получить все рецепты
@app.get("/recipes")
def get_recipes(token: str):
    payload = tokens.verify(token)
    if not payload or not payload.get("user_id", None):
        return {"message": "bad token"}

    user_items = db.get_items(payload["user_id"])
    user_categories = set()
    for item in user_items:
        if item.get("category"):
            user_categories.add(item["category"])

    recipes = db.get_recipes()
    result = []
    for r in recipes:
        ingredients = json.loads(r["ingredients_json"])
        matched = 0
        total = 0
        missing = []
        for ing in ingredients:
            if ing.get("optional"):
                continue
            total += 1
            ing_name_lower = ing["name"].lower()
            ing_cat_lower = ing["category"].lower()
            found = False
            for item in user_items:
                if item["name"].lower() == ing_name_lower:
                    found = True
                    break
                if item.get("category") and item["category"].lower() == ing_cat_lower:
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


# Засидить рецепты (одноразово)
@app.post("/recipes/seed")
def seed_recipes():
    db.seed_recipes_if_empty()
    return {"message": "ok"}


# Сгенерировать рецепт через AI
@app.post("/recipes/generate")
async def generate_recipe(req: RecipeGenerate):
    payload = tokens.verify(req.token)
    if not payload or not payload.get("user_id", None):
        return {"message": "bad token"}

    products_list = [f"- {p.get('name', '')} ({p.get('category', '')})" for p in req.user_products]
    products_text = "\n".join(products_list) if products_list else "Нет продуктов"

    api_key = os.environ.get("FIREWORKS_API_KEY", "")
    if not api_key:
        return {"message": "error: FIREWORKS_API_KEY not configured"}

    prompt = f"""Ты — генератор рецептов. У пользователя есть следующие продукты:
{products_text}

Придумай 3 разных рецепта, которые можно приготовить из этих продуктов.
Ответь СТРОГО валидным JSON объектом. Никакого текста до или после JSON. Никаких markdown-блоков.

Формат JSON:
{{
    "recipes": [
        {{
            "name": "Название",
            "description": "Описание",
            "icon": "🍲",
            "cook_time_minutes": 30,
            "servings": 2,
            "ingredients": [
                {{"name": "Продукт", "category": "Категория", "quantity": "Кол-во", "optional": false}}
            ],
            "instructions": "Шаг 1. Шаг 2."
        }}
    ]
}}

Категории: Молочное, Мясо, Рыба, Овощи, Фрукты, Бакалея, Напитки, Замороженное, Соусы и приправы, Прочее.
Если ингредиента нет у пользователя, ставь "optional": true."""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.fireworks.ai/inference/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "fireworks/deepseek-v4-flash",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 4000,
                    "response_format": {"type": "json_object"},
                },
            )
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")

            import re
            try:
                response_json = json.loads(content)
            except json.JSONDecodeError:
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    try:
                        response_json = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        return {"message": f"error: AI returned malformed JSON. Raw: {content[:300]}"}
                else:
                    return {"message": f"error: invalid AI response. Raw: {content[:300]}"}

            recipes_list = response_json.get("recipes", [])
            if not recipes_list:
                return {"message": "error: no recipes in AI response"}

            added_ids = []
            added_recipes = []
            for r in recipes_list:
                recipe_id = db.add_recipe(
                    name=r.get("name", "AI Рецепт"),
                    description=r.get("description", ""),
                    icon=r.get("icon", "🤖"),
                    cook_time=r.get("cook_time_minutes", 30),
                    servings=r.get("servings", 2),
                    ingredients_json=json.dumps(r.get("ingredients", [])),
                    instructions=r.get("instructions", ""),
                    is_ai=True,
                )
                if recipe_id > 0:
                    added_ids.append(recipe_id)
                    added_recipes.append(r)

            return {"message": "ok", "recipe_ids": added_ids, "recipes": added_recipes}
    except Exception as e:
        return {"message": f"error: {str(e)}"}
