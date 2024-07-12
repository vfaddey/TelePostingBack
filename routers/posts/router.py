from io import BytesIO
import pandas as pd
from fastapi import Form, File, UploadFile, HTTPException, APIRouter, Depends
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
import datetime
import json
from starlette.responses import JSONResponse

from routers.auth.models import User
from routers.auth.service import get_current_user
from routers.posts.schemas import Post, AddPost, parse_post_data

from .post_service import PostService
from .post_repository import PostRepository

from redis import Redis

router = APIRouter(prefix='/create_post', tags=['posts'])

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.telegram_posts
fs = AsyncIOMotorGridFSBucket(db)
posts_collection = db.posts

post_repository = PostRepository(posts_collection, fs)
post_service = PostService(post_repository, Redis())


@router.post("/", response_model=Post)
async def create_post(add_post: AddPost = Depends(parse_post_data)):
    post = await post_service.add_post(add_post)
    return post


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
            # await post_publisher.create_post(post_data)
            documents.append(post_data)

        return JSONResponse(status_code=200, content={"message": "File processed successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inserting data into MongoDB: {str(e)}")
    

@router.get('/', response_model=list[Post])
async def get_posts(current_user: User = Depends(get_current_user)):
    pass


@router.get('/{post_id}', response_model=Post)
async def get_post(post_id: str,
                   current_user: User = Depends(get_current_user)):
    pass


@router.delete('/{post_id}')
async def delete_post(post_id: str,
                      current_user: User = Depends(get_current_user)):
    pass 


@router.put('/', response_model=Post)
async def update_post(current_user: User = Depends(get_current_user)):
    pass