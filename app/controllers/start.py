"""Start / help controllers."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import UserService
from app.views import keyboards, texts

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    service = UserService(session)
    user, created = await service.get_or_create(message.from_user)

    text = texts.welcome(user.full_name) if created else texts.welcome_back(user.full_name)
    await message.answer(text, reply_markup=keyboards.main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP)


@router.callback_query(F.data == "menu:help")
async def cb_help(callback: CallbackQuery) -> None:
    await callback.message.answer(texts.HELP)
    await callback.answer()
