import asyncio
from fastapi import HTTPException
from numpy import add
from routers.telegram.bot_manager import BotManager
from .post_repository import PostRepository
from redis import Redis
from typing import Dict
import threading
from datetime import datetime, timedelta, timezone
from .schemas import Post, AddPost
from bson import ObjectId
from routers.telegram.post_publisher import PostPublisher


class PostService:
    def __init__(self, post_repository: PostRepository, broker: Redis) -> None:
        self.post_repository = post_repository
        self.broker = broker
        self.timers: Dict[str, threading.Timer] = {}
        self.post_publisher = PostPublisher(post_repository)
        asyncio.create_task(self.load_scheduled_posts())

    async def add_post(self, add_post: AddPost) -> Post:
        post = await self.post_repository.add_post(add_post)
        if post:
            if add_post.publish_now:
                await self.publish_now(post.id, post.owner_id)
            else:
                self.broker.set(post.id, post.publish_time.timestamp())
                await self.schedule_post(post.id, post.owner_id, post.publish_time)
            return post
        raise HTTPException('Не удалось добавить объект в БД')

    async def delete_post(self, post_id):
        pass

    async def update_post(self, post_id, post: Post):
        pass

    async def get_post(self, post_id: str | ObjectId):
        if isinstance(post_id, ObjectId):
            post = await self.post_repository.get_post(post_id)
        if isinstance(post_id, str):
            post = await self.post_repository.get_post(ObjectId(post_id))
        return post

    async def schedule_post(self, post_id: str, user_id: str, publish_time: datetime):
        # if publish_time.tzinfo is None: 
        #     publish_time = publish_time.replace(tzinfo=timezone.utc)
        delay = (publish_time - datetime.now(timezone.utc)).total_seconds()
        print(delay)
        if delay < 0:
            raise HTTPException(status_code=400, detail="Дата публикации указана позже текущей даты")
        self.broker.zadd('post_schedule', {post_id: publish_time.timestamp()})
        
        loop = asyncio.get_event_loop()
        timer = threading.Timer(delay, lambda: loop.create_task(self.post_publisher.fetch_post_and_send_message(post_id, user_id)))
        self.timers[post_id] = timer
        timer.start()

    async def publish_now(self, post_id: str, user_id: str):
        loop = asyncio.get_event_loop()
        thread = threading.Thread(target=lambda: loop.create_task(self.post_publisher.fetch_post_and_send_message(post_id, user_id)))
        self.timers[post_id] = thread
        thread.start()

    async def load_scheduled_posts(self):
        current_time = datetime.now().timestamp()

        scheduled_tasks = self.broker.zrangebyscore('post_schedule', min=current_time, max='+inf')

        for task in scheduled_tasks:
            post_id = task.decode('utf-8')
            post = await self.post_repository.get_post(ObjectId(post_id))
            if post:
                publish_time = datetime.fromtimestamp(float(self.broker.get(post_id)), tz=timezone.utc)
                user_id = post.owner_id
                await self.schedule_post(post_id, user_id, publish_time)
        

class UnSuccessfulDBOperationException(Exception):
    pass