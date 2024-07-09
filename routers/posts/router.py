from io import BytesIO
import pandas as pd
from fastapi import Form, File, UploadFile, HTTPException, APIRouter, Depends
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
import datetime
import json
from starlette.responses import JSONResponse

from observers.publish_observer import PublishPostObserver
from observers.save_observer import SavePostObserver
from routers.auth.models import User
from routers.auth.service import get_current_user
from routers.posts.schemas import Post
from subjects.post_publisher import PostPublisher

router = APIRouter(prefix='/create_post', tags=['posts'])

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.telegram_posts
fs = AsyncIOMotorGridFSBucket(db)
posts_collection = db.posts


post_publisher = PostPublisher()
save_post_observer = SavePostObserver(posts_collection)
post_publisher.attach(save_post_observer)
save_post_observer.attach(PublishPostObserver())


@router.post("/", response_model=Post)
async def create_post(current_user: User = Depends(get_current_user),
                      text: Optional[str] = Form(None),
                      buttons: str = Form(None),
                      publish_time: Optional[datetime.datetime] = Form(None),
                      delete_time: Optional[datetime.datetime] = Form(None),
                      publish_now: bool = Form(False),
                      photos: List[UploadFile] = File(None)):
    print(current_user)
    photo_ids = []
    if photos:
        for photo in photos:
            content = await photo.read()
            grid_in = fs.open_upload_stream(photo.filename)
            await grid_in.write(content)
            await grid_in.close()
            photo_ids.append(grid_in._id)

    button_list = []
    if buttons:
        button_list = json.loads(buttons)

    post = {
        "text": text,
        "photos": [str(x) for x in photo_ids],
        "buttons": button_list,
        "publish_now": publish_now,
        "publish_time": publish_time,
        "delete_time": delete_time,
        "posted": False
    }

    await post_publisher.create_post(post)
    return Post(**post)


@router.post("/uploadfile")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Only .xlsx and .xls are supported.")

    try:
        contents = await file.read()
        data = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    expected_columns = {'fact', 'url', 'date'}
    if not expected_columns.issubset(data.columns):
        raise HTTPException(status_code=400, detail=f"Missing one of the required columns: {expected_columns}")

    try:
        documents = []
        for _, row in data.iterrows():
            post_data = {
                "text": row['fact'],
                "photos": [row['url']],
                "buttons": [],
                "publish_now": False,
                "publish_time": pd.to_datetime(row['date']),
                "delete_time": None,
                "posted": False
            }
            await post_publisher.create_post(post_data)
            documents.append(post_data)

        return JSONResponse(status_code=200, content={"message": "File processed successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inserting data into MongoDB: {str(e)}")