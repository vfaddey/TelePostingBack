from typing import Optional
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    id: str
    username: str
    verified: bool
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None
    email: EmailStr
    channels: Optional[list] = None