from .bot_manager import BotManager
from bson import ObjectId
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorGridFSBucket, AsyncIOMotorClient
from routers.posts.schemas import Post

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
                            if not channel.startswith('@'):
                                channel = '@' + channel
                            if channel in user_channels_usernames:
                                post_in_channel = await current_bot.send_message(channel, post.text, reply_markup=markup, parse_mode='Markdown')
                                posts_in_channels.append(post_in_channel)
                        result = await self.__handle_result(post, posts_in_channels)
                        return result
        raise InvalidPostException

    async def __send_photo_message(self, post, user_id, channels: list[str]):
        markup = InlineKeyboardMarkup(row_width=2)
        user = await ausers_collection.find_one({'_id': ObjectId(user_id)})
        user_channels_usernames = [channel['username'] for channel in user.get('channels', [])]
        if len(user_channels_usernames) == 0:
            raise InvalidPostException
        photo = await self.post_repository.get_photo(post.photo_ids[0])
        if user.get('bots', None):
            for bot in user['bots']:
                if bot.get('active', None):
                    current_bot = bot_manager.get_bot(bot['api_token'])
                    if post:
                        posts_in_channels = []
                        if post.buttons:
                            markup = self.prepare_markup(post.buttons, post.id)
                        for channel in channels:
                            if not channel.startswith('@'):
                                channel = '@' + channel
                            if channel in user_channels_usernames:
                                post_in_channel = await current_bot.send_photo(channel,
                                                                               photo=photo,
                                                                               caption=post.text,
                                                                               reply_markup=markup,
                                                                               parse_mode='Markdown')
                                posts_in_channels.append(post_in_channel)
                        result = await self.__handle_result(post, posts_in_channels)
                        return result
        raise InvalidPostException

    async def __send_photo_url_message(self, post, user_id, channels: list[str]):
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
                            if not channel.startswith('@'):
                                channel = '@' + channel
                            if channel in user_channels_usernames:
                                post_in_channel = await current_bot.send_photo(channel,
                                                                               photo=post.photo_urls[0],
                                                                               caption=post.text,
                                                                               reply_markup=markup,
                                                                               parse_mode='Markdown')
                                posts_in_channels.append(post_in_channel)
                        result = await self.__handle_result(post, posts_in_channels)
                        return result
        raise InvalidPostException

    async def __send_media_group(self, post, user_id, channels: list[str]):
        user = await ausers_collection.find_one({'_id': ObjectId(user_id)})
        user_channels_usernames = [channel['username'] for channel in user.get('channels', [])]
        if len(user_channels_usernames) == 0:
            raise InvalidPostException
        photos = await self.post_repository.get_photos(post.photo_ids)
        media_group = []
        for photo in photos:
            photo.seek(0)
            if len(media_group) == 0:
                media_group.append(InputMediaPhoto(photo, caption=post.text))
            else:
                media_group.append(InputMediaPhoto(photo))

        if user.get('bots', None):
            for bot in user['bots']:
                if bot.get('active', None):
                    current_bot = bot_manager.get_bot(bot['api_token'])
                    if post:
                        posts_in_channels = []
                        for channel in channels:
                            if not channel.startswith('@'):
                                channel = '@' + channel
                            if channel in user_channels_usernames:
                                post_in_channel = await current_bot.send_media_group(channel, media=media_group, parse_mode='Markdown')
                                posts_in_channels.append(post_in_channel)
                        result = await self.__handle_result(post, posts_in_channels)
                        return result
        raise InvalidPostException
    
    async def __handle_result(self, post: Post, posts_in_channels: list):
        post_id = ObjectId(post.id)
        messages = [{'channel': message.chat.username, 'id': message.id} for message in posts_in_channels]
        try:
            await self.post_repository.mark_as_posted(post_id)
            await self.post_repository.save_message_id(post_id, messages)
            return True
        except:
            return False
        
    async def delete_post_from_chats(self, post_id, user_id):
        bot = await self.get_user_active_bot(user_id)
        post = await self.post_repository.get_post(ObjectId(post_id))
        messages = post.messages
        if messages:
            for message in messages:
                await bot.delete_message(f"@{message['channel']}", message['id'])

    async def get_user_active_bot(self, user_id):
        user = await ausers_collection.find_one({'_id': ObjectId(user_id)})
        if user.get('bots', None):
            for bot in user['bots']:
                if bot.get('active', None):
                    current_bot = bot_manager.get_bot(bot['api_token'])
                    return current_bot

    def prepare_markup(self, buttons: dict, post_id: ObjectId):
        markup = InlineKeyboardMarkup(row_width=2)
        for index, button in enumerate(buttons):
            if button['type'] == 'url':
                url_button = InlineKeyboardButton(button['text'], url=button['url'])
                markup.add(url_button)
            elif button['type'] == 'text':
                text_button = InlineKeyboardButton(button['text'],
                                                   callback_data=f'button_{button["subscriberText"]}_{button["guestText"]}')
                markup.add(text_button)
        return markup


class InvalidPostException(Exception):
    ...
