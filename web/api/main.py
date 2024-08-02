import json
import logging
import sys
from datetime import datetime, timezone

import redis.asyncio as redis
from bson import ObjectId
from config import MONGO_URL, REDIS_HOST
from fastapi import Depends, FastAPI, HTTPException, Query, status
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
async def get_messages(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    redis: Redis = Depends(get_redis),
):
    start = (page - 1) * limit
    logger.info(f"GET for page {page} with limit {limit}")
    # Generate a Redis key for this page
    redis_key = f"messages_page_{page}_limit_{limit}"

    # Retrieve messages from Redis
    cached_messages = await redis.get(redis_key)
    if cached_messages:
        logger.info(f"Retrieved messages from Redis with key {redis_key}")
        return json.loads(cached_messages)

    # Retrieve messages from MongoDB
    # without filter
    cursor = messages_collection.find().skip(start).limit(limit)
    # filter by user
    # cursor = messages_collection.find({"user_id": message.from_user.id})
    # filter by source
    # cursor = messages_collection.find({"source": "telegram"})
    # cursor = messages_collection.find({"source": "api"})
    page_of_messages = await cursor.to_list(length=limit)
    if not page_of_messages:
        raise HTTPException(status_code=404, detail="No messages found.")

    messages_list = [
        {
            # "id": str(msg["_id"]),
            # "user_id": msg["user_id"],
            "source": msg["source"],
            "message": msg["message"],
            # "timestamp": msg["timestamp"],
        }
        for msg in page_of_messages
    ]
    # cache messages in Redis for 10 minutes
    await redis.set(redis_key, json.dumps(messages_list), ex=600)
    logger.info(
        f"Retrieved messages from MongoDB and cached with key {redis_key}"
    )
    return messages_list


@app.post("/api/v1/message/", status_code=status.HTTP_201_CREATED)
async def create_message(msg: Message, redis: Redis = Depends(get_redis)):
    message_data = msg.model_dump()
    # message_data["timestamp"] = datetime.now(timezone.utc).isoformat()
    message_data["source"] = "api"
    result = await messages_collection.insert_one(message_data)
    if result.inserted_id:
        await redis_client.flushdb()  # clear redis cache
        logger.info("Deleted messages from Redis")
        return {"id": str(result.inserted_id)}
    else:
        raise HTTPException(
            status_code=500, detail="Message could not be created"
        )
