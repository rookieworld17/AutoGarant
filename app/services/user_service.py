"""Business logic for working with users.

Controllers should call services, never touch the ORM session directly.
"""
from __future__ import annotations

from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, tg_user: TelegramUser) -> tuple[User, bool]:
        """Return the user, creating it on first contact.

        Returns a ``(user, created)`` tuple.
        """
        user = await self.get_by_telegram_id(tg_user.id)
        if user is not None:
            # Keep cached profile fields fresh.
            user.username = tg_user.username
            user.full_name = tg_user.full_name
            user.language_code = tg_user.language_code
            await self._session.commit()
            return user, False

        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
            language_code=tg_user.language_code,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user, True
