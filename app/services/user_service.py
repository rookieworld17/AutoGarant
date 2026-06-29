from __future__ import annotations

import secrets

from aiogram.types import User as TelegramUser
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.tg_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_app_id(self, app_id: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.app_id == app_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Look up a user by username, case-insensitively (stored without '@')."""
        result = await self._session.execute(
            select(User).where(func.lower(User.username) == username.lower())
        )
        return result.scalar_one_or_none()

    async def _generate_app_id(self) -> str:
        """Pick a 7-digit id that isn't taken yet, retrying on collision."""
        while True:
            candidate = f"{secrets.randbelow(10_000_000):07d}"
            result = await self._session.execute(
                select(User.id).where(User.app_id == candidate)
            )
            if result.scalar_one_or_none() is None:
                return candidate

    async def get_or_create(self, tg_user: TelegramUser) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(tg_user.id)
        if user is not None:
            user.username = tg_user.username
            user.name = tg_user.full_name
            await self._session.commit()
            return user, False

        user = User(
            tg_id=tg_user.id,
            app_id=await self._generate_app_id(),
            username=tg_user.username,
            name=tg_user.full_name,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user, True
