from .bot_manager import BotManager
from bson import ObjectId
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorGridFSBucket, AsyncIOMotorClient
import asyncio


import pymongo


client = pymongo.MongoClient('mongodb://localhost:27017')
users_collection = client['telegram_posts']['users']
bot_manager = BotManager(users_collection)


client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.telegram_posts
fs = AsyncIOMotorGridFSBucket(db)
posts_collection = db.posts
ausers_collection = db.users


class PostPublisher:
    def __init__(self, post_repository) -> None:
        self.post_repository = post_repository

    async def fetch_post_and_send_message(self, post_id, user_id):
        markup = InlineKeyboardMarkup(row_width=2)
        post = await self.post_repository.get_post(ObjectId(post_id))
        user = await ausers_collection.find_one({'_id': ObjectId(user_id)})
        if user.get('bots', None):
            for bot in user['bots']:
                if bot.get('active', None):
                    current_bot = bot_manager.get_bot(bot['api_token'])
                    if post:
                        if post.buttons:
                            markup = self.prepare_markup(post.buttons, post_id)
                        post_in_channel = current_bot.send_message('@unforgetable_facts', post.text, reply_markup=markup)
                        await self.post_repository.mark_as_posted(ObjectId(post_id))

    def prepare_markup(self, buttons: dict, post_id: ObjectId):
        markup = InlineKeyboardMarkup(row_width=2)
        for index, button in enumerate(buttons):
            if button['type'] == 'url':
                url_button = InlineKeyboardButton(button['text'], url=button['url'])
                markup.add(url_button)
            elif button['type'] == 'text':
                text_button = InlineKeyboardButton(button['text'], callback_data=f'button_{post_id}_{index}')
                markup.add(text_button)
        return markup
