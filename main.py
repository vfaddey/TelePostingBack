from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.posts.router import router as posts_router
from routers.auth.router import router as auth_router
from routers.telegram.bots.router import router as bots_router
from routers.telegram.channels.router import router as channels_router

app = FastAPI()
app.include_router(posts_router)
app.include_router(auth_router)
app.include_router(bots_router)
app.include_router(channels_router)


origins = [
    'http://leetpost.ru',
    'http://www.leetpost.ru'
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    'http://93.183.68.122'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
