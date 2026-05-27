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
        return None


def get_user(user_id: int):
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    return {"id": user.id, "name": user.user_name, "email": user.email}


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
                "user_id": product.user_id,
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


"""
def check_all_users_in_db():
    users = session.query(User).all()
    print("\n=== СПИСОК ВСЕХ ПОЛЬЗОВАТЕЛЕЙ В БД ===")
    for u in users:
        print(u.id, u.user_name, u.email)
    print("======================================\n")


check_all_users_in_db()
"""
