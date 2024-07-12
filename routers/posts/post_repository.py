from .schemas import Post, AddPost
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorGridFSBucket
from fastapi import UploadFile, HTTPException
import json
from bson import ObjectId


class PostRepository:
    def __init__(self, posts_collection: AsyncIOMotorCollection, grid_fs_buckect: AsyncIOMotorGridFSBucket) -> None:
        self.posts_collection = posts_collection
        self.fs = grid_fs_buckect

    async def add_post(self, add_post: AddPost) -> Post:
        photo_ids = []
        if add_post.photos:
            photo_ids = await self._add_photos(add_post.photos)
        

        button_list = []
        if add_post.buttons:
            button_list = json.loads(add_post.buttons)

        post = {
            "text": add_post.text,
            "photos": [str(x) for x in photo_ids],
            "buttons": button_list,
            "publish_now": add_post.publish_now,
            "publish_time": add_post.publish_time,
            "delete_time": add_post.delete_time,
            "posted": False,
            "owner_id": add_post.owner_id
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

