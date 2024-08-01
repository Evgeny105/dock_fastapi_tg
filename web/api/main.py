import json
import logging
import sys
from datetime import datetime, timezone

import redis.asyncio as redis
from bson import ObjectId
from config import MONGO_URL, REDIS_HOST
from fastapi import Depends, FastAPI, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from redis.asyncio import Redis

# Setting up logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


# Pydantic model for the incoming POST request
class Message(BaseModel):
    # user_id: int
    message: str


app = FastAPI()

# Database connection
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client.bot_database
messages_collection = db.messages

# Redis connection
redis_client = redis.from_url(f"redis://{REDIS_HOST}", decode_responses=True)


async def get_redis() -> Redis:
    return redis_client


@app.get("/api/v1/messages/")
async def get_messages(redis: Redis = Depends(get_redis)):

    # Retrieve messages from Redis
    cached_messages = await redis.get("messages")
    if cached_messages:
        # logger.info("Retrieved messages from Redis")
        return json.loads(cached_messages)

    # Retrieve messages from MongoDB
    # without filter
    cursor = messages_collection.find()
    # filter by user
    # cursor = messages_collection.find({"user_id": message.from_user.id})
    # filter by source
    # cursor = messages_collection.find({"source": "telegram"})
    # cursor = messages_collection.find({"source": "api"})
    messages = await cursor.to_list(length=100)
    messages_list = [
        {
            # "id": str(msg["_id"]),
            # "user_id": msg["user_id"],
            "source": msg["source"],
            "message": msg["message"],
            # "timestamp": msg["timestamp"],
        }
        for msg in messages
    ]

    await redis.set("messages", json.dumps(messages_list))
    # logger.info("Retrieved messages from MongoDB")
    return messages_list


@app.post("/api/v1/message/", status_code=status.HTTP_201_CREATED)
async def create_message(msg: Message, redis: Redis = Depends(get_redis)):
    message_data = msg.model_dump()
    # message_data["timestamp"] = datetime.now(timezone.utc).isoformat()
    message_data["source"] = "api"
    result = await messages_collection.insert_one(message_data)
    if result.inserted_id:
        await redis.delete("messages")
        # logger.info("Deleted messages from Redis")
        return {"id": str(result.inserted_id)}
    else:
        raise HTTPException(
            status_code=500, detail="Message could not be created"
        )
