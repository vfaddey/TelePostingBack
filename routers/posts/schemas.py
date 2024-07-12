import datetime
from fastapi import Form, File, UploadFile
from typing import Optional, List
from pydantic import BaseModel


class Post(BaseModel):
    id: Optional[str] = None
    text: Optional[str]
    buttons: Optional[List[dict]]
    publish_time: Optional[datetime.datetime]
    publish_now: Optional[bool]
    delete_time: Optional[datetime.datetime]
    photos: Optional[List[str]]


class AddPost(BaseModel):
    text: Optional[str] = None
    buttons: Optional[List[dict]] = None
    publish_time: Optional[datetime.datetime] = None
    publish_now: Optional[bool] = None
    delete_time: Optional[datetime.datetime] = None
    photos: Optional[list[UploadFile]] = None


async def parse_post_data(
    text: Optional[str] = Form(None),
    buttons: str = Form(None),
    publish_time: Optional[datetime.datetime] = Form(None),
    delete_time: Optional[datetime.datetime] = Form(None),
    publish_now: bool = Form(False),
    photos: List[UploadFile] = File(None)
):
    return AddPost(
        text=text,
        buttons=buttons,
        publish_time=publish_time,
        delete_time=delete_time,
        publish_now=publish_now,
        photos=photos
    )


class UpdatePost(BaseModel):
    id: str
    text: Optional[str]
    publish_time: Optional[datetime.datetime]
    delete_time: Optional[datetime.datetime]
    photos_to_del: Optional[list[str]]