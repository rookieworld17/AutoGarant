"""Application entry point.

Run with:  python -m app
"""
from __future__ import annotations

import asyncio
import logging

from app.bot import create_bot, create_dispatcher
from app.config import settings


def setup_logging() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


async def main() -> None:
    setup_logging()
    logger = logging.getLogger("autogarant")

    bot = create_bot()
    dp = create_dispatcher()

    logger.info("Starting AutoGarant bot…")
    try:
        # Drop pending updates accumulated while the bot was offline.
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
