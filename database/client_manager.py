from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URL = os.getenv('MONGO_URL')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME')
# mongo_url = 'mongodb://localhost:27017'
# mongo_db_name = 'telegram_posts'


class MongoClientManager:
    def __init__(self, url: str, db_name: str):
        self.mongo_url = url
        self.mongo_db_name = db_name
        self.client = None

    async def __aenter__(self):
        self.client = AsyncIOMotorClient(self.mongo_url)
        database = self.client.get_database(self.mongo_db_name)
        return database

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.client.close()


async def get_users_collection():
    async with MongoClientManager(MONGO_URL, MONGO_DB_NAME) as db:
        collection = db.get_collection('users')
        yield collection


async def get_posts_collection():
    async with MongoClientManager(MONGO_URL, MONGO_DB_NAME) as db:
        collection = db.get_collection('posts')
        yield collection
