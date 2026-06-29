"""Bot and dispatcher factory — wires together storage, middlewares, routers."""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.config import settings
from app.controllers import routers
from app.database import session_factory
from app.middlewares import DatabaseMiddleware


def create_bot() -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
    )


def create_dispatcher() -> Dispatcher:
    redis = Redis.from_url(settings.redis_url)
    storage = RedisStorage(redis=redis)

    dp = Dispatcher(storage=storage)

    db_middleware = DatabaseMiddleware(session_factory)
    dp.message.middleware(db_middleware)
    dp.callback_query.middleware(db_middleware)

    dp.include_routers(*routers)

    return dp
