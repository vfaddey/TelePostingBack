from fastapi import APIRouter, Depends, HTTPException, Body

from .schemas import AddChannel, Channel

from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId

from routers.telegram.post_publisher import bot_manager

from routers.auth.service import get_current_user
from routers.auth.models import User

from database.client_manager import get_users_collection


router = APIRouter(prefix='/channels', tags=['channels'])


@router.post('/', response_model=Channel)
async def add_channel(add_channel: AddChannel = Body(...),
                      current_user: User = Depends(get_current_user),
                      users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    if not add_channel.username.startswith('@'):
        raise HTTPException(status_code=400, detail='Юзернейм канала должен начинаться с @')
    user_id = ObjectId(current_user.id)
    user_in_db = await users_collection.find_one({'_id': user_id})
    user_channels = user_in_db.get('channels', [])
    user_bots = user_in_db.get('bots', [])
    if len(user_bots) == 0:
        raise HTTPException(status_code=400, detail='У Вас нет активных ботов. Сначала нужно добавить хотя бы одного бота')
    if any(channel['username'] == add_channel.username for channel in user_channels):
        raise HTTPException(status_code=400, detail='Такой канал уже есть в списке каналов')
    
    for bot in user_bots:
        if bot['active']:
            current_bot = bot_manager.get_bot(bot['api_token'])
            if not current_bot:
                raise HTTPException(status_code=400, detail='Не удалось проверить канал')
            try:
                channel_info = await current_bot.get_chat(add_channel.username)
            except Exception:
                raise HTTPException(status_code=400, detail='Такой канал не найден')
            try:
                bot_info = await current_bot.get_me()
                await current_bot.get_chat_member(add_channel.username, bot_info.id)
            except Exception:
                raise HTTPException(status_code=400, detail=f'Ваш активный бот ({bot["api_token"]}) не состоит в канале или канал не найден')
            if channel_info.type != 'channel':
                raise HTTPException(status_code=400, detail='Этот чат не является каналом')
            channel_data = {
                'username': add_channel.username,
                'title': channel_info.title,
                'chat_id': channel_info.id
            }
            user_channels.append(channel_data)
            break
    result = await users_collection.update_one({'_id': user_id},
                                               {
                                                    '$set': {'channels': user_channels}
                                                })
    if result.modified_count > 0:
        return Channel(**channel_data)
    raise HTTPException(status_code=400, detail='Ошибка добавления в базу данных. Попробуйте еще раз позже')


@router.get('/', response_model=list[Channel])
async def get_channels(current_user: User = Depends(get_current_user),
                       users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    user_id = ObjectId(current_user.id)
    user_in_db = await users_collection.find_one({'_id': user_id})
    user_channels = user_in_db.get('channels', [])
    result = []
    for channel in user_channels:
        result.append(Channel(**channel))
    return result


@router.delete('/{username}')
async def delete_channel(username: str,
                         current_user: User = Depends(get_current_user),
                         users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    user_id = ObjectId(current_user.id)
    user_in_db = await users_collection.find_one({'_id': user_id})
    user_channels = user_in_db.get('channels', [])
    new_list = []
    for index, channel in enumerate(user_channels):
        print(channel, username)
        if not (channel.get('username', None) == username):
            new_list.append(channel)

    result = await users_collection.update_one({'_id': user_id},
                                               {
                                                   '$set': {'channels': new_list}
                                               })
    if result.modified_count > 0:
        return new_list
    raise HTTPException(status_code=400, detail='Что-то пошло не так')

