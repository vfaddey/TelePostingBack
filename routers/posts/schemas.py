import datetime
from typing import Optional, List
from pydantic import BaseModel


class Post(BaseModel):
    text: Optional[str]
    buttons: Optional[List[dict]]
    publish_time: Optional[datetime.datetime]
    delete_time: Optional[datetime.datetime]
    photos: Optional[List[str]]
