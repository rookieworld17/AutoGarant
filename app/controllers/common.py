"""Fallback controllers for anything not handled elsewhere.

This router must be included LAST so specific handlers take priority.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.types import Message

from app.views import texts

router = Router(name="common")


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer(texts.UNKNOWN)
