from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime

Base = declarative_base()
engine = create_engine("sqlite:///products.db")
Session = sessionmaker(bind=engine)
session = Session()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_name = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)

    products = relationship("Product", back_populates="user")


## замените пж password на что-то другое если надо, я хз


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String, nullable=False)
    expiration = Column(DateTime, nullable=True)
    deleted = Column(Boolean, default=False)

    user = relationship("User", back_populates="products")


Base.metadata.create_all(engine)


def find_by_email(email: str):
    return session.query(User).filter(User.email == email).first()


def create_user(username: str, email: str, passhash: str):
    new_user = User(user_name=username, email=email, password=passhash)
    session.add(new_user)
    session.commit()
    return new_user.id


def get_user(user_id: int):
    return session.query(User).filter(User.id == user_id).first()


def add_items(user_id: int, items: list):
    user = get_user(user_id)
    if not user:
        return "user not found"

    for item in items:
        expiration_s = item.get("expiration")
        expiration_date = None
        if expiration_s:
            try:
                expiration_date = datetime.fromisoformat(expiration_s)
            except ValueError:
                try:
                    expiration_date = datetime.strptime(expiration_s, "%Y-%m-%d")
                except ValueError:
                    return "BAD FROMAT!"

        new_product = Product(
            user_id=user_id,
            name=item["name"],
            expiration=expiration_date,
            deleted=False,
        )
        session.add(new_product)

    session.commit()
    return "success"


def get_items(user_id: int) -> list:
    return session.query(Product).filter(Product.user_id == user_id).all()


def items_to_delete(item_ids: list[int]):
    updated_count = (
        session.query(Product)
        .filter(Product.id.in_(item_ids))
        .update({Product.deleted: True}, synchronize_session="fetch")
    )

    session.commit()
    return f"{updated_count} items deleted"
