from typing import Optional

from pydantic import BaseModel


class AddBot(BaseModel):
    api_token: str
    chosen: Optional[bool] = None


class ChangeActiveBot(BaseModel):
    api_token: str


class DeleteBot(BaseModel):
    api_token: str
