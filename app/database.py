# app/database.py
import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "travel_planner")

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    client = get_client()
    return client[MONGO_DB]


async def ping_db() -> bool:
    try:
        client = get_client()
        await client.admin.command("ping")
        return True
    except Exception:
        return False
