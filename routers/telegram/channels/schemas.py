from pydantic import BaseModel


class Channel(BaseModel):
    username: str
    chat_id: int
    title: str


class AddChannel(BaseModel):
    username: str