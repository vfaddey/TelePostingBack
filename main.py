from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.posts.router import router as posts_router
from routers.auth.router import router as auth_router
from routers.bots.router import router as bots_router

app = FastAPI()
app.include_router(posts_router)
app.include_router(auth_router)
app.include_router(bots_router)


origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
