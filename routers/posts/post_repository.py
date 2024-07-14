from datetime import timezone

from pandas import json_normalize
from .schemas import Post, AddPost
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorGridFSBucket
from fastapi import UploadFile, HTTPException
import json
from bson import ObjectId
from io import BytesIO


class PostRepository:
    def __init__(self, posts_collection: AsyncIOMotorCollection, grid_fs_buckect: AsyncIOMotorGridFSBucket) -> None:
        self.posts_collection = posts_collection
        self.fs = grid_fs_buckect

    async def add_post(self, add_post: AddPost) -> Post:
        photo_ids = []
        if add_post.photos:
            photo_ids = await self._add_photos(add_post.photos)

        if add_post.publish_time is not None:
            if add_post.publish_time.tzinfo is None: 
                add_post.publish_time = add_post.publish_time.replace(tzinfo=timezone.utc)

        button_list = []
        if add_post.buttons:
            button_list = json.loads(add_post.buttons)

        channel_list = json.loads(add_post.channels)

        post = {
            "text": add_post.text,
            "photo_ids": [str(x) for x in photo_ids],
            "photo_urls": add_post.photo_urls,
            "buttons": button_list,
            "publish_now": add_post.publish_now,
            "publish_time": add_post.publish_time,
            "delete_time": add_post.delete_time,
            "posted": False,
            "owner_id": add_post.owner_id,
            "channels": channel_list
        }

        result = await self.posts_collection.insert_one(post)
        if result.inserted_id:
            del post['_id']
            post['id'] = str(result.inserted_id)
        return Post(**post)


    async def _add_photos(self, files: list[UploadFile]) -> list:
        photo_ids = []
        for file in files:
            content = await file.read()
            grid_in = self.fs.open_upload_stream(file.filename)
            await grid_in.write(content)
            await grid_in.close()
            photo_ids.append(grid_in._id)
        return photo_ids
    
    async def get_photos(self, photo_ids: list[str]) -> list[BytesIO]:
        photos = []
        async for photo_id in photo_ids:
            photo_data = bytearray()
            async for chunk in self.fs.open_download_stream(photo_id):
                photo_data.extend(chunk)
            photos.append(BytesIO(photo_data))
        return photos
    
    async def get_photo(self, photo_id: str | ObjectId) -> BytesIO:
        photo_data = bytearray()
        async for chunk in self.fs.open_download_stream(photo_id):
            photo_data.extend(chunk)
        return BytesIO(photo_data)
    
    async def get_posts(self, user_id: str, posted: bool) -> list[Post]:
        post_list = []
        result = self.posts_collection.find({
            'owner_id': user_id,
            'posted': posted
        })
        if result:
            async for post in result:
                post['id'] = str(post['_id'])
                del post['_id']
                post_list.append(Post(**post))
            return post_list
        raise HTTPException(status_code=400, detail='Не найдена информация о постах')
    
    async def get_post(self, post_id: ObjectId) -> Post:
        result = await self.posts_collection.find_one({'_id': post_id})
        if result:
            return Post(**result)
        raise HTTPException('Не удалось найти пост')

    async def update_post(self, post_id, post: Post):
        pass

    async def delete_post(self, post_id):
        pass

    async def mark_as_posted(self, post_id) -> bool:
        result = await self.posts_collection.update_one({'_id': post_id},
                                                        {
                                                            '$set': {
                                                                'posted': True
                                                            }
                                                        })
        return result.matched_count > 0

