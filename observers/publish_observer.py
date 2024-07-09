from bson import ObjectId
from celery.result import AsyncResult
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from telebot.types import InlineKeyboardMarkup
import asyncio
import nest_asyncio
from telegram.post_collector import prepare_markup

from observers.observer import Observer
from celery import Celery

from telegram.bot_manager import bot_manager

celery_app = Celery('publish_observer', broker='redis://localhost:6379')

bot_manager.add_bot('6759802763:AAHFgRRSPBlgrhC735yJVB2IjB4pMu6CWCo')

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.telegram_posts
fs = AsyncIOMotorGridFSBucket(db)
posts_collection = db.posts


async def fetch_post_and_send_message(post_id):
    result = await posts_collection.find_one({'_id': ObjectId(post_id['id'])})
    markup = InlineKeyboardMarkup(row_width=1)
    current_bot = bot_manager.get_bot('6759802763:AAHFgRRSPBlgrhC735yJVB2IjB4pMu6CWCo')
    if result:
        if result['buttons']:
            markup = prepare_markup(result['buttons'], post_id['id'])
        current_bot.send_message('@unforgetable_facts', result['text'], reply_markup=markup)


@celery_app.task
def publish_post(post_id):
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(fetch_post_and_send_message(post_id))


class PublishPostObserver(Observer):

    def update(self, data):
        post_id = {'id': str(data['_id'])}
        if data['publish_now']:
            task = publish_post.delay(post_id)
        elif data['publish_time']:
            task = publish_post.apply_async((post_id,), eta=data['publish_time'])
        data['task_id'] = task.id

    def cancel_task(self, task_id):
        result = AsyncResult(task_id, app=celery_app)
        result.revoke()
