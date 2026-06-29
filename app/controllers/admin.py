"""Admin panel controllers.

A single ``/admin`` command opens an inline panel (admins only). From there the
admin can pay out accumulated commission. Everything stays in one edited-in-place
message, matching the rest of the bot.
"""
from __future__ import annotations

import logging
from contextlib import suppress
from decimal import Decimal

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services import PayoutService, crypto_pay
from app.views import keyboards, texts

logger = logging.getLogger(__name__)

router = Router(name="admin")

MIN_PAYOUT = Decimal("1")


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_id_list


async def _payout_summary(
    session: AsyncSession,
) -> tuple[str, InlineKeyboardMarkup]:
    """Summary card: count + total of unpaid commissions, the last payout, and a
    'pay now' button when there's something to pay and a recipient is configured."""
    service = PayoutService(session)
    count, total, max_id = await service.pending()
    last = await service.last_payout()
    can_pay = (
        settings.commission_recipient_id is not None
        and max_id is not None
        and total >= MIN_PAYOUT
    )
    text = texts.admin_payout_summary(
        pending_count=count,
        pending_sum=total,
        last_amount=last.amount if last else None,
        last_at=last.created_at if last else None,
        min_payout=MIN_PAYOUT,
    )
    return text, keyboards.admin_payout(can_pay)


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    """Open the admin panel. Silently ignored for non-admins."""
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(texts.ADMIN_PANEL, reply_markup=keyboards.admin_panel())


@router.callback_query(F.data == "admin:panel")
async def cb_admin_panel(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            texts.ADMIN_PANEL, reply_markup=keyboards.admin_panel()
        )
    await callback.answer()


@router.callback_query(F.data == "admin:payout")
async def cb_admin_payout(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Show the commission payout summary."""
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    text, markup = await _payout_summary(session)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "admin:payout:confirm")
async def cb_admin_payout_confirm(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Transfer the accumulated commission to the admin, then (only on success)
    settle the swept transactions and record the payout."""
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    async def _show(text: str) -> None:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(text, reply_markup=keyboards.admin_back())

    recipient = settings.commission_recipient_id
    if recipient is None:
        await _show(texts.ADMIN_PAYOUT_NO_RECIPIENT)
        await callback.answer()
        return

    service = PayoutService(session)
    _count, total, max_id = await service.pending()
    if max_id is None or total <= 0:
        await _show(texts.ADMIN_PAYOUT_NOTHING)
        await callback.answer()
        return
    if total < MIN_PAYOUT:
        await _show(texts.admin_payout_below_min(MIN_PAYOUT))
        await callback.answer()
        return

    try:
        await crypto_pay.create_transfer(
            user_id=recipient,
            amount=total,
            spend_id=f"comm-{max_id}",
            comment="Вывод комиссии AutoGarant",
        )
    except crypto_pay.CryptoPayError as exc:
        logger.warning("Commission payout failed: %s", exc)
        await _show(texts.ADMIN_PAYOUT_ERROR)
        await callback.answer()
        return

    await service.settle(max_id=max_id, amount=total)
    await _show(texts.admin_payout_done(total))
    await callback.answer("Готово")
