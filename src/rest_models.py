from pydantic import BaseModel


class QRText(BaseModel):
    qrraw: str
    token: str


class NewUser(BaseModel):
    name: str
    password: str
    token: str


class NewUsername(BaseModel):
    name: str
    token: str


class NewPassword(BaseModel):
    password: str
    token: str


class NewEmail(BaseModel):
    email_token: str
    user_token: str


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


class NotificationTokens(BaseModel):
    token: str
    web_token: str | None = None
    tel_token: str | None = None
    email_notification: bool = True


class NewRecipe(BaseModel):
    token: str
    name: str
    description: str
    icon: str
    cook_time_minutes: int
    servings: int
    ingredients_json: str
    instructions: str
