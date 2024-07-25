from pydantic import BaseModel, EmailStr


class User(BaseModel):
    id: str
    username: str
    verified: bool
    telegram_id: int
    telegram_username: str
    email: EmailStr