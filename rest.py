from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


@app.get("/")
async def root():
    return {"message": "Hello, FastAPI!"}


@app.post("/items")
async def create_item(item: Item):
    return {
        "status": "success",
        "item": item.name
    }