from pydantic import BaseModel


class QRText(BaseModel):
    qrraw: str
    token: str


class NewUser(BaseModel):
    name: str
    password: str
    token: str


class Login(BaseModel):
    email: str
    password: str


class NewItems(BaseModel):
    items: list
    token: str


class DropItems(BaseModel):
    item_ids: list[int]
    token: str


class UPDItems(BaseModel):
    token: str
    items_upd: list[tuple[int,dict]]


class CodeVerification(BaseModel):
    email: str
    code: str
