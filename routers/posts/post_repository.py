from datetime import timezone
import stat

from pandas import json_normalize
from .schemas import Post, AddPost, UpdatePost
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
        button_list = []
        if add_post.buttons:
            button_list = json.loads(add_post.buttons)

        if add_post.photos:
            if len(add_post.photos) > 1 and len(button_list) > 0:
                raise HTTPException(status_code=400,
                                    detail='Нельзя создавать кнопки, если в альбоме больше одной картинки')

        if add_post.photo_urls:
            if len(add_post.photo_urls) > 1 and len(button_list) > 0:
                raise HTTPException(status_code=400,
                                    detail='Нельзя создавать кнопки, если в альбоме больше одной картинки')

        if add_post.publish_time and add_post.delete_time:
            if add_post.delete_time < add_post.publish_time:
                raise HTTPException(status_code=400,
                                    detail='Дата удаления не может быть раньше даты публикации')

        if (not add_post.publish_now) and (not add_post.publish_time):
            raise HTTPException(status_code=400,
                                detail='Необходимо выбрать время публикации')

        photo_ids = []
        if add_post.photos:
            photo_ids = await self._add_photos(add_post.photos)

        if add_post.publish_time is not None:
            if add_post.publish_time.tzinfo is None:
                add_post.publish_time = add_post.publish_time.replace(tzinfo=timezone.utc)

        channel_list = json.loads(add_post.channels)
        if len(channel_list) == 0:
            raise HTTPException('Нужно выбрать хотя бы один канал для публикации')

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
        if isinstance(photo_ids[0], str):
            photo_ids = [ObjectId(x) for x in photo_ids]
        for photo_id in photo_ids:
            photo_data = bytearray()
            async for chunk in await self.fs.open_download_stream(photo_id):
                photo_data.extend(chunk)
            photos.append(BytesIO(photo_data))
        return photos

    async def get_photo(self, photo_id: str | ObjectId) -> BytesIO:
        photo_data = bytearray()
        if isinstance(photo_id, str):
            photo_id = ObjectId(photo_id)
        async for chunk in await self.fs.open_download_stream(photo_id):
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
            result['id'] = str(result['_id'])
            del result['_id']
            return Post(**result)
        raise HTTPException('Не удалось найти пост')

    async def update_post(self, post: UpdatePost) -> Post:
        prev_post = await self.get_post(ObjectId(post.id))
        if prev_post.posted:
            raise HTTPException(status_code=400, detail='Пост уже опубликован в канале')
        button_list = []
        if post.buttons:
            button_list = json.loads(post.buttons)

        if post.photos:
            if len(post.photos) > 1 and len(button_list) > 0:
                raise HTTPException(status_code=400,
                                    detail='Нельзя создавать кнопки, если в альбоме больше одной картинки')

        if post.photo_urls:
            if len(post.photo_urls) > 1 and len(button_list) > 0:
                raise HTTPException(status_code=400,
                                    detail='Нельзя создавать кнопки, если в альбоме больше одной картинки')

        if post.publish_time and post.delete_time:
            if post.delete_time < post.publish_time:
                raise HTTPException(status_code=400,
                                    detail='Дата удаления не может быть раньше даты публикации')

        if (not post.publish_now) and (not post.publish_time):
            raise HTTPException(status_code=400,
                                detail='Необходимо выбрать время публикации')

        if post.publish_time is not None:
            if post.publish_time.tzinfo is None:
                post.publish_time = post.publish_time.replace(tzinfo=timezone.utc)

        channel_list = json.loads(post.channels)
        if len(channel_list) == 0:
            raise HTTPException('Нужно выбрать хотя бы один канал для публикации')

        to_change = {
            "text": post.text,
            "photo_urls": post.photo_urls,
            "buttons": button_list,
            "publish_now": post.publish_now,
            "publish_time": post.publish_time,
            "delete_time": post.delete_time,
            "channels": channel_list
        }
        new_post = Post(id=post.id,
                        owner_id=prev_post.owner_id,
                        photo_ids=prev_post.photo_ids,
                        posted=prev_post.posted,
                        **to_change)
        result = await self.posts_collection.update_one({'_id': ObjectId(post.id)},
                                                        {
                                                            '$set': to_change
                                                        }, upsert=True)
        if result.modified_count > 0:
            return new_post

    async def delete_post(self, post_id, user_id):
        if not self.posts_collection.find_one({"_id": ObjectId(post_id)}):
            raise HTTPException(status_code=404, detail="Этот пост не найден")

        result = await self.posts_collection.delete_one({
            "_id": ObjectId(post_id),
            "owner_id": user_id
        })
        if result.deleted_count == 0:
            raise HTTPException(status_code=401, detail='Вы не являетесь создаталем поста')
        return True

    async def mark_as_posted(self, post_id) -> bool:
        result = await self.posts_collection.update_one({'_id': post_id},
                                                        {
                                                            '$set': {
                                                                'posted': True
                                                            }
                                                        })
        return result.matched_count > 0

    async def save_message_id(self, post_id: ObjectId, messages: list[dict]):
        result = await self.posts_collection.update_one({'_id': post_id},
                                                        {
                                                            '$set': {'messages': messages}
                                                        }, upsert=True)
        return result.modified_count > 0
