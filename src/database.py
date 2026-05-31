from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Float,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime

Base = declarative_base()
engine = create_engine("sqlite:///products.db")
Session = sessionmaker(bind=engine)
session = Session()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)

    products = relationship("Product", back_populates="user")
    history = relationship("Histories", back_populates="user")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String, nullable=False)
    category = Column(String, default=None)
    expiration = Column(DateTime, nullable=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    deleted = Column(Boolean, default=False)

    user = relationship("User", back_populates="products")


class Histories(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    qr = Column(String, nullable=False)

    user = relationship("User", back_populates="history")


class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    icon = Column(String, default="🍽️")
    cook_time_minutes = Column(Integer, default=30)
    servings = Column(Integer, default=2)
    ingredients_json = Column(String, nullable=False)  # JSON строка
    instructions = Column(String, nullable=False)
    is_ai_generated = Column(Boolean, default=False)


Base.metadata.create_all(engine)


def find_by_email(email: str):
    user = session.query(User).filter(User.email == email).first()
    if not user:
        return None
    return {
        "id": user.id,
        "name": user.user_name,
        "email": user.email,
        "passhash": user.password,
    }


def create_user(username: str, email: str, passhash: str):
    try:
        new_user = User(user_name=username, email=email, password=passhash)
        session.add(new_user)
        session.commit()
        return new_user.id
    except IntegrityError:
        session.rollback()
        return "exists"
    except:
        session.rollback()
        return None


def get_user(user_id: int):
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    return {"id": user.id, "name": user.user_name, "email": user.email, "password": user.password}


def update_user(user_id: int, newdata: dict):
    newdata.pop("id", None) # id менять нельзя
    
    user = (
        session.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        return "user not found"
    
    try:
        session.query(User).filter(User.id == user_id).update(newdata)
        session.commit()
        return "ok"
    except IntegrityError:
        session.rollback()
        return "email exists"
    except Exception as e:
        session.rollback()
        return f"error: {e}"


def add_items(user_id: int, items: list):
    user = get_user(user_id)
    if not user:
        return "user not found"

    for item in items:
        category_s = item.get("category")

        expiration_s = item.get("expiration")
        expiration_date = None

        quantity_s = item.get("quantity")
        quantity_stn = 1.0

        unit_s = item.get("unit")
        unit_base = unit_s if unit_s else "шт"

        if expiration_s:
            try:
                expiration_date = datetime.fromisoformat(expiration_s)
            except ValueError:
                try:
                    expiration_date = datetime.strptime(expiration_s, "%Y-%m-%d")
                except ValueError:
                    expiration_date = None

        if quantity_s:
            try:
                quantity_stn = float(quantity_s)
            except ValueError:
                quantity_stn = 1.0

        new_product = Product(
            user_id=user_id,
            name=item["name"],
            category=category_s,
            expiration=expiration_date,
            quantity=quantity_stn,
            unit=unit_base,
            deleted=False,
        )
        session.add(new_product)

    session.commit()
    return "success"


def get_items(user_id: int) -> list:
    products = session.query(Product).filter(Product.user_id == user_id).all()

    result = []
    for product in products:
        result.append(
            {
                "id": product.id,
                "name": product.name,
                "category": product.category,
                "expiration": (
                    product.expiration.strftime("%Y-%m-%d")
                    if product.expiration
                    else None
                ),
                "quantity": product.quantity,
                "unit": product.unit,
                "deleted": product.deleted,
            }
        )
    return result


def items_to_delete(user_id: int, item_ids: list[int]):
    updated_count = (
        session.query(Product)
        .filter(Product.id.in_(item_ids), Product.user_id == user_id)
        .update({Product.deleted: True}, synchronize_session="fetch")
    )
    session.commit()
    return f"{updated_count} items deleted"


def update_items(user_id: int, items_upd: list) -> str:
    updated_count = 0

    for item_id, changes in items_upd:
        # защита от негодяев
        changes.pop("id", None)
        changes.pop("user_id", None)
        changes.pop("deleted", None)

        expiration_s = changes.get("expiration")
        expiration_date = None

        if expiration_s:
            try:
                expiration_date = datetime.fromisoformat(expiration_s)
            except ValueError:
                try:
                    expiration_date = datetime.strptime(expiration_s, "%Y-%m-%d")
                except ValueError:
                    expiration_date = None

        changes["expiration"] = expiration_date

        product = (
            session.query(Product)
            .filter(Product.id == item_id, Product.user_id == user_id)
            .first()
        )

        if product:
            session.query(Product).filter(Product.id == item_id).update(changes)
            updated_count += 1

    session.commit()
    return f"{updated_count} items updated"


def get_recipes() -> list:
    recipes = session.query(Recipe).all()
    result = []
    for r in recipes:
        result.append({
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "icon": r.icon,
            "cook_time_minutes": r.cook_time_minutes,
            "servings": r.servings,
            "ingredients_json": r.ingredients_json,
            "instructions": r.instructions,
            "is_ai_generated": r.is_ai_generated,
        })
    return result


def add_recipe(name: str, description: str, icon: str, cook_time: int, servings: int, ingredients_json: str, instructions: str, is_ai: bool = False) -> int:
    try:
        new_recipe = Recipe(
            name=name,
            description=description,
            icon=icon,
            cook_time_minutes=cook_time,
            servings=servings,
            ingredients_json=ingredients_json,
            instructions=instructions,
            is_ai_generated=is_ai,
        )
        session.add(new_recipe)
        session.commit()
        return new_recipe.id
    except Exception as e:
        session.rollback()
        return -1


def seed_recipes_if_empty():
    import json
    recipes = session.query(Recipe).all()
    if len(recipes) > 0:
        return

    recipes_data = [
        ("Борщ", "Классический украинский борщ", "🍲", 90, 6,
         json.dumps([
             {"name": "Свёкла", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Капуста", "category": "Овощи", "quantity": "300 г", "optional": False},
             {"name": "Картофель", "category": "Овощи", "quantity": "3 шт", "optional": False},
             {"name": "Морковь", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Лук", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Говядина", "category": "Мясо", "quantity": "400 г", "optional": False},
             {"name": "Томатная паста", "category": "Соусы и приправы", "quantity": "2 ст.л.", "optional": False},
             {"name": "Чеснок", "category": "Овощи", "quantity": "3 зуб.", "optional": False},
         ]),
         "1. Сварите бульон из говядины (1.5 часа). 2. Нарежьте картофель кубиками, добавьте в бульон. 3. Натрите свёклу и морковь, обжарьте с томатной пастой. 4. Нашинкуйте капусту, добавьте в бульон. 5. Добавьте зажарку, чеснок, специи. 6. Варите ещё 10 минут. Подавайте со сметаной."),
        ("Оливье", "Новогодний салат с колбасой", "🥗", 40, 4,
         json.dumps([
             {"name": "Картофель", "category": "Овощи", "quantity": "3 шт", "optional": False},
             {"name": "Морковь", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Яйца", "category": "Молочное", "quantity": "4 шт", "optional": False},
             {"name": "Колбаса", "category": "Мясо", "quantity": "300 г", "optional": False},
             {"name": "Огурцы маринованные", "category": "Соусы и приправы", "quantity": "3 шт", "optional": False},
             {"name": "Горошек", "category": "Бакалея", "quantity": "1 банка", "optional": False},
             {"name": "Майонез", "category": "Соусы и приправы", "quantity": "150 г", "optional": False},
         ]),
         "1. Отварите картофель, морковь и яйца. 2. Нарежьте все ингредиенты кубиками. 3. Добавьте горошек. 4. Заправьте майонезом, посолите, перемешайте."),
        ("Блины", "Тонкие блины на молоке", "🥞", 30, 4,
         json.dumps([
             {"name": "Молоко", "category": "Молочное", "quantity": "500 мл", "optional": False},
             {"name": "Яйца", "category": "Молочное", "quantity": "2 шт", "optional": False},
             {"name": "Мука", "category": "Бакалея", "quantity": "200 г", "optional": False},
             {"name": "Сахар", "category": "Бакалея", "quantity": "2 ст.л.", "optional": False},
             {"name": "Масло растительное", "category": "Бакалея", "quantity": "2 ст.л.", "optional": False},
         ]),
         "1. Взбейте яйца с сахаром. 2. Добавьте половину молока, перемешайте. 3. Постепенно всыпьте муку, размешивая до однородности. 4. Добавьте остаток молока и масло. 5. Жарьте на разогретой сковороде с двух сторон."),
        ("Пельмени", "Домашние пельмени с мясом", "🥟", 60, 4,
         json.dumps([
             {"name": "Мука", "category": "Бакалея", "quantity": "400 г", "optional": False},
             {"name": "Яйца", "category": "Молочное", "quantity": "1 шт", "optional": False},
             {"name": "Вода", "category": "Напитки", "quantity": "150 мл", "optional": False},
             {"name": "Свинина", "category": "Мясо", "quantity": "300 г", "optional": False},
             {"name": "Говядина", "category": "Мясо", "quantity": "200 г", "optional": False},
             {"name": "Лук", "category": "Овощи", "quantity": "2 шт", "optional": False},
         ]),
         "1. Замесите тесто из муки, яйца и воды. 2. Прокрутите мясо и лук через мясорубку. 3. Раскатайте тесто, вырежьте кружки. 4. В каждый положите фарш, защипните. 5. Варите в кипящей воде 5-7 минут после всплытия."),
        ("Курица с картошкой", "Запечённая курица с картофелем", "🍗", 60, 4,
         json.dumps([
             {"name": "Курица", "category": "Мясо", "quantity": "1 шт", "optional": False},
             {"name": "Картофель", "category": "Овощи", "quantity": "6 шт", "optional": False},
             {"name": "Майонез", "category": "Соусы и приправы", "quantity": "3 ст.л.", "optional": False},
             {"name": "Чеснок", "category": "Овощи", "quantity": "4 зуб.", "optional": False},
         ]),
         "1. Разрежьте курицу на порции. 2. Нарежьте картофель дольками. 3. Смешайте майонез с чесноком. 4. Выложите всё в форму, смажьте соусом. 5. Запекайте при 180°C 45 минут."),
        ("Паста Карбонара", "Итальянская паста с беконом", "🍝", 25, 2,
         json.dumps([
             {"name": "Спагетти", "category": "Бакалея", "quantity": "200 г", "optional": False},
             {"name": "Бекон", "category": "Мясо", "quantity": "150 г", "optional": False},
             {"name": "Яйца", "category": "Молочное", "quantity": "2 шт", "optional": False},
             {"name": "Сыр", "category": "Молочное", "quantity": "50 г", "optional": False},
         ]),
         "1. Отварите спагетти. 2. Обжарьте бекон. 3. Смешайте яйца с тёртым сыром. 4. Соедините горячую пасту с беконом, влейте яичную смесь, быстро перемешайте."),
        ("Греческий салат", "Свежий салат с фетой", "🥗", 15, 2,
         json.dumps([
             {"name": "Помидоры", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Огурцы", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Перец болгарский", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Сыр фета", "category": "Молочное", "quantity": "150 г", "optional": False},
             {"name": "Маслины", "category": "Бакалея", "quantity": "100 г", "optional": False},
             {"name": "Масло оливковое", "category": "Соусы и приправы", "quantity": "2 ст.л.", "optional": False},
         ]),
         "1. Нарежьте овощи крупными кусками. 2. Добавьте фету и маслины. 3. Заправьте оливковым маслом, посолите."),
        ("Жареная картошка", "Картошка с луком на сковороде", "🥔", 30, 3,
         json.dumps([
             {"name": "Картофель", "category": "Овощи", "quantity": "6 шт", "optional": False},
             {"name": "Лук", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Масло растительное", "category": "Бакалея", "quantity": "3 ст.л.", "optional": False},
         ]),
         "1. Нарежьте картофель брусочками. 2. Разогрейте масло на сковороде. 3. Жарьте картофель на среднем огне 20 минут, помешивая. 4. Добавьте лук за 5 минут до готовности. Посолите."),
        ("Сырники", "Творожные сырники со сметаной", "🧀", 25, 3,
         json.dumps([
             {"name": "Творог", "category": "Молочное", "quantity": "400 г", "optional": False},
             {"name": "Яйца", "category": "Молочное", "quantity": "1 шт", "optional": False},
             {"name": "Мука", "category": "Бакалея", "quantity": "3 ст.л.", "optional": False},
             {"name": "Сахар", "category": "Бакалея", "quantity": "2 ст.л.", "optional": False},
             {"name": "Сметана", "category": "Молочное", "quantity": "100 г", "optional": True},
         ]),
         "1. Смешайте творог, яйцо, муку и сахар. 2. Сформируйте шарики, обваляйте в муке. 3. Жарьте на масле по 3 минуты с каждой стороны. Подавайте со сметаной."),
        ("Щи", "Русские щи из свежей капусты", "🍲", 60, 4,
         json.dumps([
             {"name": "Капуста", "category": "Овощи", "quantity": "400 г", "optional": False},
             {"name": "Картофель", "category": "Овощи", "quantity": "3 шт", "optional": False},
             {"name": "Морковь", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Лук", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Говядина", "category": "Мясо", "quantity": "300 г", "optional": False},
         ]),
         "1. Сварите бульон. 2. Добавьте нарезанный картофель. 3. Нашинкуйте капусту, добавьте в бульон. 4. Обжарьте лук и морковь, добавьте в щи. 5. Варите до готовности."),
        ("Котлеты", "Домашние мясные котлеты", "🥩", 40, 4,
         json.dumps([
             {"name": "Фарш", "category": "Мясо", "quantity": "500 г", "optional": False},
             {"name": "Лук", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Хлеб", "category": "Бакалея", "quantity": "2 ломтика", "optional": False},
             {"name": "Яйца", "category": "Молочное", "quantity": "1 шт", "optional": False},
         ]),
         "1. Замочите хлеб в молоке. 2. Смешайте фарш, лук, хлеб и яйцо. 3. Сформируйте котлеты. 4. Обанилируйте в муке, жарьте по 5 минут с каждой стороны."),
        ("Омлет", "Пышный омлет с молоком", "🍳", 15, 2,
         json.dumps([
             {"name": "Яйца", "category": "Молочное", "quantity": "4 шт", "optional": False},
             {"name": "Молоко", "category": "Молочное", "quantity": "100 мл", "optional": False},
             {"name": "Масло сливочное", "category": "Молочное", "quantity": "20 г", "optional": False},
         ]),
         "1. Взбейте яйца с молоком и солью. 2. Вылейте на разогретую сковороду с маслом. 3. Готовьте под крышкой на медленном огне 7-10 минут."),
        ("Винегрет", "Классический винегрет", "🥗", 30, 4,
         json.dumps([
             {"name": "Свёкла", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Картофель", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Морковь", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Огурцы маринованные", "category": "Соусы и приправы", "quantity": "2 шт", "optional": False},
             {"name": "Горошек", "category": "Бакалея", "quantity": "100 г", "optional": False},
             {"name": "Масло подсолнечное", "category": "Соусы и приправы", "quantity": "2 ст.л.", "optional": False},
         ]),
         "1. Отварите свёклу, картофель, морковь. 2. Нарежьте кубиками все овощи и огурцы. 3. Добавьте горошек. 4. Заправьте маслом, перемешайте."),
        ("Макароны по-флотски", "Макароны с мясным фаршем", "🍝", 30, 3,
         json.dumps([
             {"name": "Макароны", "category": "Бакалея", "quantity": "300 г", "optional": False},
             {"name": "Фарш", "category": "Мясо", "quantity": "300 г", "optional": False},
             {"name": "Лук", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Томатная паста", "category": "Соусы и приправы", "quantity": "2 ст.л.", "optional": True},
         ]),
         "1. Отварите макароны. 2. Обжарьте фарш с луком. 3. Добавьте томатную пасту. 4. Смешайте с макаронами."),
        ("Рассольник", "Суп с солёными огурцами", "🍲", 60, 4,
         json.dumps([
             {"name": "Картофель", "category": "Овощи", "quantity": "3 шт", "optional": False},
             {"name": "Огурцы маринованные", "category": "Соусы и приправы", "quantity": "3 шт", "optional": False},
             {"name": "Перловка", "category": "Бакалея", "quantity": "100 г", "optional": False},
             {"name": "Морковь", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Лук", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Говядина", "category": "Мясо", "quantity": "300 г", "optional": False},
         ]),
         "1. Сварите бульон с перловкой. 2. Добавьте картофель. 3. Обжарьте лук, морковь и нарезанные огурцы. 4. Добавьте зажарку в суп, варите 10 минут."),
        ("Тушёная капуста", "Капуста тушёная с мясом", "🥬", 50, 3,
         json.dumps([
             {"name": "Капуста", "category": "Овощи", "quantity": "500 г", "optional": False},
             {"name": "Свинина", "category": "Мясо", "quantity": "200 г", "optional": False},
             {"name": "Морковь", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Томатная паста", "category": "Соусы и приправы", "quantity": "1 ст.л.", "optional": True},
         ]),
         "1. Нарежьте мясо, обжарьте. 2. Добавьте морковь, лук. 3. Нашинкуйте капусту, добавьте к мясу. 4. Тушите под крышкой 30 минут."),
        ("Жареная рыба", "Рыба жареная в муке", "🐟", 25, 2,
         json.dumps([
             {"name": "Рыба", "category": "Рыба", "quantity": "4 стейка", "optional": False},
             {"name": "Мука", "category": "Бакалея", "quantity": "100 г", "optional": False},
             {"name": "Масло растительное", "category": "Бакалея", "quantity": "3 ст.л.", "optional": False},
             {"name": "Лимон", "category": "Фрукты", "quantity": "0.5 шт", "optional": True},
         ]),
         "1. Обваляйте рыбу в муке с солью. 2. Жарьте на масле по 4 минуты с каждой стороны. 3. Сбрызните лимоном."),
        ("Плов", "Узбекский плов с бараниной", "🍚", 90, 6,
         json.dumps([
             {"name": "Рис", "category": "Бакалея", "quantity": "400 г", "optional": False},
             {"name": "Баранина", "category": "Мясо", "quantity": "500 г", "optional": False},
             {"name": "Морковь", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Лук", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Чеснок", "category": "Овощи", "quantity": "1 головка", "optional": False},
         ]),
         "1. Обжарьте мясо. 2. Добавьте лук и морковь (зирвак). 3. Залейте водой, тушите 30 мин. 4. Добавьте рис и чеснок. 5. Готовьте на медленном огне, пока рис не впитает воду."),
        ("Грибы жареные", "Жареные грибы с картошкой", "🍄", 35, 3,
         json.dumps([
             {"name": "Грибы", "category": "Овощи", "quantity": "300 г", "optional": False},
             {"name": "Картофель", "category": "Овощи", "quantity": "4 шт", "optional": False},
             {"name": "Лук", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Сметана", "category": "Молочное", "quantity": "2 ст.л.", "optional": True},
         ]),
         "1. Нарежьте грибы и картофель. 2. Обжарьте картофель до полуготовности. 3. Добавьте грибы и лук. 4. Жарьте до готовности. По желанию добавьте сметану."),
        ("Каша овсяная", "Овсяная каша с фруктами", "🥣", 15, 2,
         json.dumps([
             {"name": "Овсянка", "category": "Бакалея", "quantity": "100 г", "optional": False},
             {"name": "Молоко", "category": "Молочное", "quantity": "200 мл", "optional": False},
             {"name": "Сахар", "category": "Бакалея", "quantity": "1 ст.л.", "optional": True},
             {"name": "Масло сливочное", "category": "Молочное", "quantity": "10 г", "optional": True},
         ]),
         "1. Залейте овсянку молоком. 2. Доведите до кипения. 3. Варите 5 минут, помешивая. 4. Добавьте сахар и масло."),
        ("Шарлотка", "Яблочный пирог", "🍰", 50, 6,
         json.dumps([
             {"name": "Яблоки", "category": "Фрукты", "quantity": "4 шт", "optional": False},
             {"name": "Яйца", "category": "Молочное", "quantity": "4 шт", "optional": False},
             {"name": "Мука", "category": "Бакалея", "quantity": "200 г", "optional": False},
             {"name": "Сахар", "category": "Бакалея", "quantity": "150 г", "optional": False},
         ]),
         "1. Взбейте яйца с сахаром. 2. Добавьте муку. 3. Нарежьте яблоки. 4. Выложите яблоки в форму, залейте тестом. 5. Выпекайте при 180°C 35 минут."),
        ("Минестроне", "Итальянский овощной суп", "🍲", 40, 4,
         json.dumps([
             {"name": "Картофель", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Морковь", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Помидоры", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Кабачок", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Макароны", "category": "Бакалея", "quantity": "100 г", "optional": False},
         ]),
         "1. Нарежьте все овощи. 2. Сварите бульон, добавьте картофель и морковь. 3. Через 10 мин добавьте остальные овощи и макароны. 4. Варите до готовности."),
        ("Куриный суп", "Лёгкий суп с курицей и лапшой", "🍲", 45, 4,
         json.dumps([
             {"name": "Курица", "category": "Мясо", "quantity": "300 г", "optional": False},
             {"name": "Картофель", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Морковь", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Лапша", "category": "Бакалея", "quantity": "100 г", "optional": False},
         ]),
         "1. Сварите куриный бульон. 2. Добавьте картофель и морковь. 3. Через 15 минут добавьте лапшу. 4. Варите ещё 5 минут."),
        ("Голубцы", "Голубцы в сметанном соусе", "🥬", 70, 4,
         json.dumps([
             {"name": "Капуста", "category": "Овощи", "quantity": "1 кочан", "optional": False},
             {"name": "Фарш", "category": "Мясо", "quantity": "400 г", "optional": False},
             {"name": "Рис", "category": "Бакалея", "quantity": "100 г", "optional": False},
             {"name": "Морковь", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Сметана", "category": "Молочное", "quantity": "200 г", "optional": False},
         ]),
         "1. Отварите капусту, разберите на листья. 2. Смешайте фарш с рисом. 3. Заверните фарш в листья. 4. Обжарьте морковь, добавьте сметану. 5. Тушите голубцы в соусе 40 минут."),
        ("Тёплый салат", "Салат с курицей и овощами", "🥗", 25, 2,
         json.dumps([
             {"name": "Курица", "category": "Мясо", "quantity": "200 г", "optional": False},
             {"name": "Помидоры", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Салат айсберг", "category": "Овощи", "quantity": "100 г", "optional": False},
             {"name": "Сыр", "category": "Молочное", "quantity": "50 г", "optional": True},
         ]),
         "1. Обжарьте курицу кусочками. 2. Нарежьте овощи. 3. Выложите салат, сверху курицу и овощи. 4. Посыпьте сыром."),
        ("Картофельная запеканка", "Запеканка с мясом и картофелем", "🥘", 60, 4,
         json.dumps([
             {"name": "Картофель", "category": "Овощи", "quantity": "5 шт", "optional": False},
             {"name": "Фарш", "category": "Мясо", "quantity": "300 г", "optional": False},
             {"name": "Сыр", "category": "Молочное", "quantity": "100 г", "optional": False},
             {"name": "Молоко", "category": "Молочное", "quantity": "100 мл", "optional": False},
         ]),
         "1. Отварите картофель, сделайте пюре. 2. Обжарьте фарш. 3. Выложите слоями: пюре, фарш, пюре. 4. Посыпьте сыром. 5. Запекайте при 180°C 25 минут."),
        ("Уха", "Рыбный суп из сёмги", "🍲", 50, 4,
         json.dumps([
             {"name": "Рыба", "category": "Рыба", "quantity": "400 г", "optional": False},
             {"name": "Картофель", "category": "Овощи", "quantity": "3 шт", "optional": False},
             {"name": "Морковь", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Лук", "category": "Овощи", "quantity": "1 шт", "optional": False},
         ]),
         "1. Сварите рыбный бульон. 2. Добавьте картофель и морковь. 3. Обжарьте лук, добавьте в суп. 4. Варите до готовности картофеля."),
        ("Оладьи", "Пышные оладьи на кефире", "🥞", 25, 3,
         json.dumps([
             {"name": "Кефир", "category": "Молочное", "quantity": "250 мл", "optional": False},
             {"name": "Мука", "category": "Бакалея", "quantity": "200 г", "optional": False},
             {"name": "Яйца", "category": "Молочное", "quantity": "1 шт", "optional": False},
             {"name": "Сахар", "category": "Бакалея", "quantity": "2 ст.л.", "optional": False},
         ]),
         "1. Смешайте кефир, яйцо, сахар. 2. Постепенно добавьте муку. 3. Жарьте на разогретой сковороде с двух сторон."),
        ("Творожная запеканка", "Запеканка из творога", "🧁", 50, 4,
         json.dumps([
             {"name": "Творог", "category": "Молочное", "quantity": "500 г", "optional": False},
             {"name": "Яйца", "category": "Молочное", "quantity": "2 шт", "optional": False},
             {"name": "Мука", "category": "Бакалея", "quantity": "3 ст.л.", "optional": False},
             {"name": "Сахар", "category": "Бакалея", "quantity": "4 ст.л.", "optional": False},
         ]),
         "1. Смешайте творог, яйца, муку, сахар. 2. Выложите в форму. 3. Выпекайте при 180°C 35 минут."),
        ("Овощное рагу", "Рагу из сезонных овощей", "🥘", 45, 3,
         json.dumps([
             {"name": "Картофель", "category": "Овощи", "quantity": "3 шт", "optional": False},
             {"name": "Кабачок", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Помидоры", "category": "Овощи", "quantity": "2 шт", "optional": False},
             {"name": "Морковь", "category": "Овощи", "quantity": "1 шт", "optional": False},
             {"name": "Лук", "category": "Овощи", "quantity": "1 шт", "optional": False},
         ]),
         "1. Нарежьте все овощи. 2. Обжарьте лук и морковь. 3. Добавьте картофель, тушите 15 мин. 4. Добавьте кабачок и помидоры. 5. Тушите ещё 15 минут."),
    ]

    for r in recipes_data:
        add_recipe(*r)


"""
def check_all_users_in_db():
    users = session.query(User).all()
    print("\n=== СПИСОК ВСЕХ ПОЛЬЗОВАТЕЛЕЙ В БД ===")
    for u in users:
        print(u.id, u.user_name, u.email)
    print("======================================\n")


check_all_users_in_db()
"""
