from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserInDB(BaseModel):
    username: str
    email: EmailStr
    hashed_password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    sub: str
    username: str | None = None
    email: EmailStr

class RefreshTokenRequest(BaseModel):
    token: str


class TelegramConfirmRequest(BaseModel):
    temp_key: str
    telegram_id: int
    username: str