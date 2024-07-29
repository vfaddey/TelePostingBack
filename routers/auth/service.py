from datetime import datetime, timedelta
from bson import ObjectId
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from database.client_manager import get_users_collection
from .schemas import TokenData
from .utils import verify_password
from .models import User

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login')

from .keys.keys import PUBLIC_KEY, PRIVATE_KEY


async def authenticate_user(email: str,
                            password: str,
                            users_collection: AsyncIOMotorCollection
):
    user = await users_collection.find_one({"email": email})
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    user['id'] = str(user['_id'])
    return User(**user)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme),
                           users_collection: AsyncIOMotorCollection = Depends(get_users_collection)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")
        email: str = payload.get('email')
        sub: str = payload.get('sub')
        if username is None:
            raise credentials_exception
        token_data = TokenData(sub=sub, username=username, email=email)
    except JWTError:
        raise credentials_exception
    user = await users_collection.find_one({"_id": ObjectId(token_data.sub)})
    if user is None:
        raise credentials_exception
    user['id'] = str(user['_id'])
    return User(**user)


async def get_current_verified_user(token: str = Depends(oauth2_scheme),
                                    users_collection: AsyncIOMotorCollection = Depends(get_users_collection)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Необходимо подтвердить аккаунт",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")
        email: str = payload.get('email')
        sub: str = payload.get('sub')
        if username is None:
            raise credentials_exception
        token_data = TokenData(sub=sub, username=username, email=email)
    except JWTError:
        raise credentials_exception
    user = await users_collection.find_one({"_id": ObjectId(token_data.sub)})
    if (user is None) or (not user.get('verified', False)):
        raise credentials_exception
    user['id'] = str(user['_id'])
    return User(**user)