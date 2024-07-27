import datetime
import json
from fastapi import Form, File, UploadFile, Depends
from typing import Optional, List
from pydantic import BaseModel
from routers.auth.models import User
from routers.auth.service import get_current_user, get_current_verified_user


class Post(BaseModel):
    id: Optional[str] = None
    text: Optional[str]
    buttons: Optional[list[dict]]
    publish_time: Optional[datetime.datetime]
    publish_now: Optional[bool]
    delete_time: Optional[datetime.datetime]
    photo_ids: Optional[list[str]] = []
    photo_urls: Optional[list[str]] = []
    owner_id: Optional[str] = None
    posted: Optional[bool] = None
    channels: list[str]
    messages: list[dict] = []


class AddPost(BaseModel):
    text: Optional[str] = None
    buttons: Optional[str] = None
    publish_time: Optional[datetime.datetime] = None
    publish_now: Optional[bool] = None
    delete_time: Optional[datetime.datetime] = None
    photos: Optional[list[UploadFile]] = None
    photo_urls: Optional[list[str]] = None
    owner_id: Optional[str] = None
    channels: str


async def parse_post_data(
    text: Optional[str] = Form(None),
    buttons: str = Form(None),
    publish_time: Optional[datetime.datetime] = Form(None),
    delete_time: Optional[datetime.datetime] = Form(None),
    publish_now: bool = Form(False),
    photos: List[UploadFile] = File(None),
    channels: str = Form(None),
    current_user: User = Depends(get_current_verified_user),
):
    return AddPost(
        text=text,
        buttons=buttons,
        publish_time=publish_time,
        delete_time=delete_time,
        publish_now=publish_now,
        photos=photos,
        owner_id=current_user.id,
        channels=channels
    )


class UpdatePost(BaseModel):
    id: str
    text: Optional[str]
    publish_time: Optional[datetime.datetime]
    delete_time: Optional[datetime.datetime]
    photos_to_del: Optional[list[str]]