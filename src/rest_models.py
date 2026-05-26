from pydantic import BaseModel


class QRText(BaseModel):
    user_id: int
    qrraw: str
    token: str


class Register(BaseModel):
    name: str
    email: str
    password: str


class Login(BaseModel):
    email: str
    password: str


class NewItems(BaseModel):
    user_id: int
    items: list
    token: str


class DropItems(BaseModel):
    item_ids: list[int]
    user_id: int
    token: str


class UPDItems(BaseModel):
    user_id: int
    token: str
    items_upd: list[tuple[int,dict]]
