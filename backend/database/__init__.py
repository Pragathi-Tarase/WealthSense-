from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, MONGODB_DB_NAME
import logging

class Database:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect_db(cls):
        """Create database connection."""
        try:
            cls.client = AsyncIOMotorClient(MONGODB_URL)
            cls.db = cls.client[MONGODB_DB_NAME]
            logging.info("Connected to MongoDB.")
        except Exception as e:
            logging.error(f"Could not connect to MongoDB: {e}")
            raise e

    @classmethod
    async def close_db(cls):
        """Close database connection."""
        if cls.client:
            cls.client.close()
            logging.info("MongoDB connection closed.")
