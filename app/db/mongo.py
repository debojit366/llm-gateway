# app/db/mongo.py
import os
from motor.motor_asyncio import AsyncIOMotorClient

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db_helper = MongoDB()

async def connect_to_mongo():
    mongo_url = os.getenv("MONGODB_URL", "mongodb://mongodb:27017/llm_gateway_db")
    db_helper.client = AsyncIOMotorClient(mongo_url)
    db_helper.db = db_helper.client.get_default_database()
    print("✅ Connected to MongoDB successfully!")

async def close_mongo_connection():
    if db_helper.client:
        db_helper.client.close()
        print("❌ MongoDB connection closed.")