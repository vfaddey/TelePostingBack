from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URL = os.getenv('MONGO_URL')

client = AsyncIOMotorClient(MONGO_URL)
db = client.telegram_posts
users_collection = db.users
