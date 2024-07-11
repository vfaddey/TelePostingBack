from .post_repository import PostRepository
from redis import Redis
from typing import Dict
import threading
from .schemas import Post, AddPost



class PostService:
    def __init__(self, post_repository: PostRepository, broker: Redis) -> None:
        self.post_repository = post_repository
        self.broker = broker
        self.timers: Dict[str, threading.Timer] = {}

    async def add_post(self, add_post: AddPost) -> Post:
        post = await self.post_repository.add_post(add_post)
        if post:
            await self.schedule_post(post.id)
            return post
        raise UnSuccessfulDBOperationException('Не удалось добавить объект в БД')

    async def delete_post(self, post_id):
        pass

    async def update_post(self, post_id, post: Post):
        pass

    async def schedule_post(self, post_id):
        pass

    async def load_scheduled_posts(self):
        pass
        

class UnSuccessfulDBOperationException(Exception):
    pass