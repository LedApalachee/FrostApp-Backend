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

def add_product(products):
    session.add_all(products)
    session.commit()

def pull_products():
    products = session.query(Product).all()
    return products
