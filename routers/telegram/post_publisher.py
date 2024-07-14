from turtle import pos
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
        post = await self.post_repository.get_post(ObjectId(post_id))
        channels = post.channels
        if len(channels) == 0:
            return
        photos = post.photo_ids
        photo_urls = post.photo_urls
        if photo_urls is None:
            photo_urls = []
        try:
            if len(photos) == 0 and len(photo_urls) == 0:
                return await self.__send_text_message(post, user_id, channels)
            elif len(photos) == 1:
                return await self.__send_photo_message(post, user_id, channels)
            elif len(photo_urls) == 1:
                return await self.__send_photo_url_message(post, user_id, channels)
            elif len(photos) > 1:
                return await self.__send_media_group(post, user_id, channels)
        except InvalidPostException:
            return

    async def __send_text_message(self, post, user_id, channels: list[str]):
        markup = InlineKeyboardMarkup(row_width=2)
        user = await ausers_collection.find_one({'_id': ObjectId(user_id)})
        user_channels_usernames = [channel['username'] for channel in user.get('channels', [])]
        if len(user_channels_usernames) == 0:
            raise InvalidPostException
        
        if user.get('bots', None):
            for bot in user['bots']:
                if bot.get('active', None):
                    current_bot = bot_manager.get_bot(bot['api_token'])
                    if post:
                        posts_in_channels = []
                        if post.buttons:
                            markup = self.prepare_markup(post.buttons, post.id)
                        for channel in channels:
                            if channel in user_channels_usernames:
                                post_in_channel = await current_bot.send_message(channel, post.text, reply_markup=markup)
                                posts_in_channels.append(post_in_channel)
                        await self.post_repository.mark_as_posted(ObjectId(post.id))
                        return post_in_channel
        raise InvalidPostException

    async def __send_photo_message(self, post, user_id, channels: list[str]):
        pass

    async def __send_photo_url_message(self, post, user_id, channels: list[str]):
        pass

    async def __send_media_group(self, post, user_id, channels: list[str]):
        pass

    def prepare_markup(self, buttons: dict, post_id: ObjectId):
        markup = InlineKeyboardMarkup(row_width=2)
        for index, button in enumerate(buttons):
            if button['type'] == 'url':
                url_button = InlineKeyboardButton(button['text'], url=button['url'])
                markup.add(url_button)
            elif button['type'] == 'text':
                text_button = InlineKeyboardButton(button['text'], callback_data=f'button_{button["subscriberText"]}_{button["guestText"]}')
                markup.add(text_button)
        return markup


class InvalidPostException(Exception):
    ...