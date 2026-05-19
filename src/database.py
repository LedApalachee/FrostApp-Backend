from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()
engine = create_engine("sqlite:///products.db")
Session = sessionmaker(bind=engine)
session = Session()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    data = Column(DateTime)

Base.metadata.create_all(engine)

users_db = []
users_next_id = 0

items_db = []
items_next_id = 0


def find_by_email(email: str):
    for user in users_db:
        if user["email"] == email:
            return user
    return None


def create_user(username: str, email: str, passhash: str):
    global users_next_id
    users_db.append({"id": users_next_id, "name": username, "email": email, "passhash": passhash})
    users_next_id += 1
    return users_db[-1]["id"]


def get_user(user_id: int):
    for user in users_db:
        if user["id"] == user_id:
            return user
    return None


def add_items(user_id: int, items: list):
    global items_next_id
    for item in items:
        items_db.append({"id": items_next_id, "user_id": user_id, "name": item["name"], "expiration": item["expiration"], "deleted": False})
        items_next_id += 1
    return "success"


def get_items(user_id: int) -> list:
    found = []
    for item in items_db:
        if item["user_id"] == user_id:
            found.append(item)
    return found


def items_to_delete(item_ids: list[int]):
    i = 0
    for item in items_db:
        if item["id"] in item_ids:
            item["deleted"] = True
            i += 1
    return f"{i} items deleted"
