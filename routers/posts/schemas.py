import datetime
from typing import Optional, List
from pydantic import BaseModel
from fastapi import UploadFile


class Post(BaseModel):
    id: Optional[str] = None
    text: Optional[str]
    buttons: Optional[List[dict]]
    publish_time: Optional[datetime.datetime]
    publish_now: Optional[bool]
    delete_time: Optional[datetime.datetime]
    photos: Optional[List[str]]


class AddPost(BaseModel):
    text: Optional[str]
    buttons: Optional[List[dict]]
    publish_time: Optional[datetime.datetime]
    publish_now: Optional[bool]
    delete_time: Optional[datetime.datetime]
    photos: Optional[UploadFile]