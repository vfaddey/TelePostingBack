from datetime import timedelta
from re import T


from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorCollection
from redis import Redis

from database.client_manager import get_users_collection
from .models import User
from .schemas import UserCreate, Token, RefreshTokenRequest, TelegramConfirmRequest
from .service import authenticate_user, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES, \
    REFRESH_TOKEN_EXPIRE_DAYS, create_refresh_token, PUBLIC_KEY, ALGORITHM
from .utils import hash_password, generate_random_base64
from bson import ObjectId

from dotenv import load_dotenv
import os

load_dotenv()

REDIS_URL = os.getenv('REDIS_URL')
REDIS_PORT = os.getenv('REDIS_PORT')

router = APIRouter(prefix='/auth', tags=['auth'])
redis = Redis(host=REDIS_URL, port=REDIS_PORT)


@router.post("/sign_up", response_model=User)
async def register(user: UserCreate,
                   users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    user_in_db = await users_collection.find_one({"email": user.email})
    if user_in_db:
        raise HTTPException(status_code=400, detail="Пользователь с такой почтой уже существует")
    hashed_password = hash_password(user.password)
    result = await users_collection.insert_one({
        'username': user.username,
        'email': user.email,
        'hashed_password': hashed_password,
        'verified': False
    })
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password, id=str(result.inserted_id))
    return new_user


@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(),
                                 users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    user = await authenticate_user(form_data.username, form_data.password, users_collection)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        'sub': user.id,
        'username': user.username,
        'email': user.email,
        'verified': user.verified
    }
    access_token = create_access_token(
        data=payload, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data=payload, expires_delta=refresh_token_expires
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest,
                        users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    token = request.token
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        id: str = payload.get("sub")
        if id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await users_collection.find_one({"_id": ObjectId(id)})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data=payload, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get('/confirm')
async def get_temp_key(current_user: User = Depends(get_current_user)):
    if current_user.verified:
        raise HTTPException(status_code=400, detail='Ваш профиль уже подтвержден')
    temp_key = generate_random_base64()
    redis.set(temp_key, current_user.id)
    redis.expire(temp_key, 125)
    return {'temp_key': temp_key}


@router.post('/confirm')
async def confirm_with_telegram(request: TelegramConfirmRequest,
                                users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    user_id = redis.get(request.temp_key).decode('utf-8')
    if user_id:
        result = await users_collection.update_one({'_id': ObjectId(user_id)},
                                             {
                                                 '$set': {
                                                     'verified': True,
                                                     'telegram_id': request.telegram_id,
                                                     'telegram_username': request.username
                                                 }
                                             }, upsert=True)
        if result.modified_count > 0:
            redis.delete(request.temp_key)
            return {'message': 'ok'}
    raise HTTPException(status_code=400, detail='Не получилось обработать запрос или токен неверный')
