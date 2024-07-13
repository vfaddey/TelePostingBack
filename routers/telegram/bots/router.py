from fastapi import APIRouter, Depends, HTTPException, status, Body
from motor.motor_asyncio import AsyncIOMotorCollection
from database.client_manager import get_users_collection
from routers.auth.models import User
from routers.auth.service import get_current_user
from routers.telegram.bots.schemas import AddBot, ChangeActiveBot
from routers.telegram.post_publisher import bot_manager

router = APIRouter(prefix='/bots', tags=['bots'])


@router.post('/add')
async def add_bot(request: AddBot = Body(...),
                  current_user: User = Depends(get_current_user),
                  users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):

    if bot_manager._check_bot(request.api_token):
        pass
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Неподходящий Api токен')

    result = await users_collection.find_one({'username': current_user.username})
    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Данные о пользователе не найдены')
    bots = result.get('bots', [])
    if any(bot['api_token'] == request.api_token for bot in bots):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Такой бот уже существует')

    await users_collection.update_one({'username': current_user.username},
                                      {
                                          '$push': {'bots': {
                                                  'api_token': request.api_token,
                                                  'active': request.chosen
                                              }
                                          }
                                      }, upsert=True)
    bot_manager.add_bot(request.api_token)

    return request


@router.get('/')
async def get_user_bots(current_user: User = Depends(get_current_user),
                        users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    username = current_user.username
    result = await users_collection.find_one({'username': username})
    if result:
        if result['bots']:
            bots = result['bots']
            return bots
        return []
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Данные о пользователе не найдены')


@router.put('/')
async def change_bot(request: ChangeActiveBot,
                     current_user: User = Depends(get_current_user),
                     users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    username = current_user.username
    result = await users_collection.find_one({'username': username})

    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Данные о пользователе не найдены')

    bots = result.get('bots', [])

    if not any(bot['api_token'] == request.api_token for bot in bots):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Бот не найден')

    for bot in bots:
        bot['active'] = False

    for bot in bots:
        if bot['api_token'] == request.api_token:
            bot['active'] = True

    result = await users_collection.update_one(
        {'username': username},
        {'$set': {'bots': bots}}
    )
    if result.modified_count > 0:
        bot_manager.add_bot(request.api_token)
        return {'message': 'ok', 'active_bot': request.api_token}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Не получилось обновить данные')


@router.delete('/{api_token}')
async def delete_bot(api_token: str,
                     current_user: User = Depends(get_current_user),
                     users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    result = await users_collection.find_one({'username': current_user.username})
    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Данные о пользователе не найдены')

    bots = result.get('bots', [])

    if not any(bot['api_token'] == api_token for bot in bots):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Бот не найден')

    res = {}
    for index, bot in enumerate(bots):
        if bot['api_token'] == api_token:
            res = bot
            del bots[index]

    if len(bots) > 0:
        if not all(bot['active'] for bot in bots):
            bots[0]['active'] = True
    else:
        res = {'message': 'ok'}

    result = await users_collection.update_one({'username': current_user.username},
                                      {
                                          '$set': {
                                              'bots': bots
                                          }
                                      }
                                      )
    if result.modified_count > 0:
        bot_manager.delete_bot(api_token)
    return res
