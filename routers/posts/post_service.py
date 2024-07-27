import asyncio
from fastapi import HTTPException
from .post_repository import PostRepository
from redis import Redis
import threading
from datetime import datetime, timezone
from .schemas import Post, AddPost
from bson import ObjectId
from routers.telegram.post_publisher import PostPublisher


class PostService:
    def __init__(self, post_repository: PostRepository, broker: Redis) -> None:
        self.post_repository = post_repository
        self.broker = broker
        self.timers: dict[str, threading.Thread] = {}
        self.post_publisher = PostPublisher(post_repository)
        asyncio.create_task(self.load_scheduled_posts())

    async def add_post(self, add_post: AddPost) -> Post:
        post = await self.post_repository.add_post(add_post)
        if post:
            if post.publish_now:
                await self.publish_now(post.id, post.owner_id)
            else:
                self.broker.set(post.id, post.publish_time.timestamp())
                await self.schedule_post(post.id, post.owner_id, post.publish_time)
            if post.delete_time:
                self.broker.set(f'delete:{post.id}', post.delete_time.timestamp())
                await self.schedule_delete(post.id, post.owner_id, post.delete_time)
            return post
        raise HTTPException('Не удалось добавить объект в БД')

    async def delete_post(self, post_id, user_id):
        result = await self.post_repository.delete_post(post_id, user_id)
        if result and post_id in self.timers:
            self.timers[post_id].cancel()

        if result:
            self.broker.delete(post_id)
            self.broker.zrem('post_schedule', post_id)
        return {'message': 'ok'}

    async def update_post(self, post_id: str | ObjectId, post: Post):
        pass

    async def get_post(self, post_id: str | ObjectId) -> Post:
        if isinstance(post_id, ObjectId):
            post = await self.post_repository.get_post(post_id)
            return post
        if isinstance(post_id, str):
            post = await self.post_repository.get_post(ObjectId(post_id))
            return post
        else:
            raise TypeError('Неверный тип')

    async def get_posts(self, user_id, posted=False) -> list[Post]:
        return await self.post_repository.get_posts(user_id, posted)

    async def schedule_post(self, post_id: str, user_id: str, publish_time: datetime):
        delay = (publish_time - datetime.now(timezone.utc)).total_seconds()
        if delay < 0:
            raise HTTPException(status_code=400, detail="Дата публикации указана позже текущей даты")

        self.broker.zadd('post_schedule', {post_id: publish_time.timestamp()})
        self.broker.expire(post_id, int(delay + 60 * 60))

        loop = asyncio.get_event_loop()
        timer = threading.Timer(delay, lambda: loop.create_task(
            self.post_publisher.fetch_post_and_send_message(post_id, user_id)))
        self.timers[post_id] = timer
        timer.start()

    async def schedule_delete(self, post_id: str, user_id: str, delete_time: datetime):
        delay_delete = (delete_time - datetime.now(timezone.utc)).total_seconds()
        if delay_delete < 0:
            raise HTTPException(status_code=400, detail="Дата удаления указана позже текущей даты")

        self.broker.expire(f'delete:{post_id}', int(delay_delete + 60 * 60))

        loop = asyncio.get_event_loop()
        timer = threading.Timer(delay_delete,
                                lambda: loop.create_task(self.post_publisher.delete_post_from_chats(post_id, user_id)))
        self.timers[f'delete_{post_id}'] = timer
        timer.start()

    async def publish_now(self, post_id: str, user_id: str):
        loop = asyncio.get_event_loop()
        thread = threading.Thread(
            target=lambda: loop.create_task(self.post_publisher.fetch_post_and_send_message(post_id, user_id)))
        self.timers[post_id] = thread
        thread.start()

    async def load_scheduled_posts(self):
        current_time = datetime.now().timestamp()

        scheduled_tasks = self.broker.zrangebyscore('post_schedule', min=current_time, max='+inf')

        for task in scheduled_tasks:
            post_id = task.decode('utf-8')
            post = await self.post_repository.get_post(ObjectId(post_id))
            user_id = post.owner_id
            if post:
                publish_time = datetime.fromtimestamp(float(self.broker.get(post_id)), tz=timezone.utc)
                await self.schedule_post(post_id, user_id, publish_time)
                try:
                    delete_time = datetime.fromtimestamp(float(self.broker.get(f'delete:{post_id}')), tz=timezone.utc)
                    await self.schedule_delete(post_id, user_id, delete_time)
                except Exception:
                    ...


class UnSuccessfulDBOperationException(Exception):
    pass