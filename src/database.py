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
    notifications = relationship("Notification", back_populates="user")


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
    fp = Column(
        Integer, nullable=False, unique=True
    )  # ФПД чека, по нему проверяем уникальность - не допускаем дублей

    user = relationship("User", back_populates="history")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    web_token = Column(String, default=None)
    tel_token = Column(String, default=None)
    email_notification = Column(Boolean, default=False)

    user = relationship("User", back_populates="notifications")


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
        new_user = User(user_name=username.lower(), email=email, password=passhash)
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
    return {
        "id": user.id,
        "name": user.user_name,
        "email": user.email,
        "password": user.password,
    }


def update_user(user_id: int, newdata: dict):
    newdata.pop("id", None)  # id менять нельзя

    user = session.query(User).filter(User.id == user_id).first()

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
    return "ok"


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


def get_qrs(user_id: int) -> list:
    qrs = session.query(Histories).filter(Histories.user_id == user_id).all()
    result = []
    for qr in qrs:
        result.append({"id": qr.id, "qrraw": qr.qr, "fp": qr.fp})
    return result


def add_qr(user_id: int, qrraw: str, fp: int):
    user = get_user(user_id)
    if not user:
        return "user not found"

    new_qr = Histories(user_id=user_id, qr=qrraw, fp=fp)
    session.add(new_qr)

    try:
        session.commit()
        return "ok"
    except IntegrityError:
        session.rollback()
        return "exists"
    except:
        session.rollback()
        return "undefined error"


def save_user_notification_tokens(
    user_id: int, web_token: str, tel_token: str, email_notification: bool
):
    try:
        setting = (
            session.query(Notification).filter(Notification.user_id == user_id).first()
        )

        if setting:
            if web_token is not None:
                setting.web_token = web_token
            if tel_token is not None:
                setting.tel_token = tel_token
            setting.email_notification = email_notification
        else:
            setting = Notification(
                user_id=user_id,
                web_token=web_token,
                tel_token=tel_token,
                email_notification=email_notification,
            )
            session.add(setting)

        session.commit()
        return "ok"
    except Exception as e:
        session.rollback()
        return f"error: {e}"


def all_users():
    users = session.query(User).all()
    print("\n=== СПИСОК ВСЕХ ПОЛЬЗОВАТЕЛЕЙ В БД ===")
    for u in users:
        print(u.id, u.user_name, u.email, u.password)
    print("======================================\n")


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


def get_recipe(id: int):
    recipe = session.query(Recipe).filter(Recipe.id == id).first()
    if not recipe:
        return None
    
    return {
        "id": recipe.id,
        "name": recipe.name,
        "description": recipe.description,
        "icon": recipe.icon,
        "cook_time_minutes": recipe.cook_time_minutes,
        "servings": recipe.servings,
        "ingredients_json": recipe.ingredients_json,
        "instructions": recipe.instructions,
        "is_ai_generated": recipe.is_ai_generated
    }


def add_recipe(name: str, description: str, icon: str, cook_time: int, servings: int, ingredients_json: str, instructions: str, is_ai: bool = False):
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
        return "ok"
    except Exception as e:
        session.rollback()
        return f"error: {e}"
