from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from motor.motor_asyncio import AsyncIOMotorCollection

from database.client_manager import get_users_collection
from .models import User
from .schemas import UserCreate, Token
from .service import authenticate_user, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES, \
    REFRESH_TOKEN_EXPIRE_DAYS, create_refresh_token, PUBLIC_KEY, ALGORITHM
from .utils import hash_password

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post("/sign_up", response_model=User)
async def register(user: UserCreate,
                   users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    user_in_db = await users_collection.find_one({"email": user.email})
    if user_in_db:
        raise HTTPException(status_code=400, detail="Пользователь с такой почтой уже существует")
    hashed_password = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    await users_collection.insert_one(new_user.dict())
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
        'email': user.email
    }
    access_token = create_access_token(
        data=payload, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data=payload, expires_delta=refresh_token_expires
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh_token(token: str,
                        users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
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
    user = await users_collection.find_one({"username": username})
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




