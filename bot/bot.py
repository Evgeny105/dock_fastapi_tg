import asyncio
import io
import json
import logging
import sys

import aiohttp
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BufferedInputFile, FSInputFile, Message
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.markdown import hbold
from config import TOKEN_API, MONGO_URL, REDIS_HOST
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis

# Setting up logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Initialize database connection
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client.bot_database
messages_collection = db.messages

# Redis connection
redis_client = redis.from_url(f"redis://{REDIS_HOST}", decode_responses=True)

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()


# Checking environment variables
if TOKEN_API == "":
    logger.critical("TOKEN_API is not set")
if MONGO_URL == "":
    logger.critical("MONGO_URL is not set")
if REDIS_HOST == "":
    logger.critical("REDIS_HOST is not set")


# info messages to admins
# @dp.startup()
# async def start_bot(bot: Bot) -> None:
#     await bot.send_message(123456789, text="Bot is started")
#     logger.info("Bot is started")


# @dp.shutdown()
# async def stop_bot(bot: Bot) -> None:
#     await bot.send_message(123456789, text="Bot is stopped")
#     logger.info("Bot is stopped")


@dp.message(Command("add"))
async def command_add_handler(message: Message, command: CommandObject) -> None:
    """
    This handler receives messages with `/add` command
    """
    if command.args is None:
        await message.answer(
            "Please, send me /add and a message to add to the system"
        )
        return
    message_data = {
        "source": "telegram",
        # "user_id": message.from_user.id,
        "message": command.args,
        # "timestamp": message.date.isoformat(),
    }
    # Save message to the MongoDB
    result = await messages_collection.insert_one(message_data)
    if result.inserted_id:
        await redis_client.flushdb()  # clear redis cache
        logger.info("Deleted messages from Redis")
        await message.answer(f"Message\n{command.args}\nadded to the system")
    else:
        await message.answer("Failed to add the message to the system")


@dp.message(Command("list"))
async def command_list_handler(
    message: Message, command: CommandObject
) -> None:
    """
    This handler receives messages with `/list` command
    """
    # Parse command arguments for pagination
    args = command.args
    if args:
        try:
            parts = args.split()
            page = int(parts[1])
            limit = int(parts[3])
        except (IndexError, ValueError):
            await message.answer(
                "Invalid format. Use `/list page {page_number} limit {page_size}`"
            )
            return
    else:
        # Default values
        page = 1
        limit = 10

    start = (page - 1) * limit
    end = start + limit

    # Retrieve messages from Redis
    redis_key = f"messages_page_{page}_limit_{limit}"
    cached_messages = await redis_client.get(redis_key)
    if cached_messages:
        page_of_messages = json.loads(cached_messages)
        logger.info(f"Retrieved messages from Redis with key {redis_key}")
    else:
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
            await message.answer("No messages found.")
            return

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
        await redis_client.set(redis_key, json.dumps(messages_list), ex=600)
        logger.info(
            f"Retrieved messages from MongoDB and cached with key {redis_key}"
        )

    response = f"Messages from the system (page {page}, limit {limit}):\n"
    response += "\n".join(
        f"{msg['source']}: {msg['message']}" for msg in page_of_messages
    )
    await message.answer(response)


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await message.answer(
        f"Hello, {hbold(message.from_user.full_name)}!\n"
        + "I'm a bot, use commands:\n"
        + " /add {message} for adding message to the system\n"
        + " /list for getting first 10 messages"
        + " /list page {page_number} limit {page_size} for getting messages with pagination"
    )


@dp.message()
async def echo_handler(message: types.Message) -> None:
    """
    Handler will forward receive a message back to the sender
    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


async def main() -> None:
    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    bot = Bot(
        TOKEN_API, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    # And the run events dispatching
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
