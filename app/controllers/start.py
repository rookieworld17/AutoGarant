"""Start / main-menu controllers."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import session_factory
from app.models import User
from app.services import (
    OPPOSITE_ROLE,
    DealService,
    TransactionService,
    UserService,
    crypto_pay,
    get_usd_rub_rate,
)
from app.states import DealStates, SearchStates, WalletStates
from app.views import keyboards, texts

logger = logging.getLogger(__name__)

router = Router(name="start")

_DEPOSIT_MIN = Decimal("1")
_WITHDRAW_MIN = Decimal("1")
_DEAL_MIN = Decimal("1")
_INVOICE_TTL = 300
_POLL_INTERVAL = 5
_CENTS = Decimal("0.01")

_DEALS_PER_PAGE = 5

_CANCEL_PENDING = ("cancelling", "escrow_cancel")

_DEAL_TTL = 15 * 60
_SWEEP_INTERVAL = 30

_watchers: dict[int, asyncio.Task] = {}


async def _edit_section(callback: CallbackQuery, text: str, markup) -> None:
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


async def _deposit_in_rub(deposit: Decimal) -> Decimal | None:
    """Convert a USD deposit to RUB at the current rate, or None if unavailable."""
    rate = await get_usd_rub_rate()
    return deposit * rate if rate is not None else None


def _parse_amount(raw: str) -> Decimal | None:
    """Parse a user-typed amount, tolerating commas, dots and spaces.

    '12,5' / '12.5' → Decimal('12.5'); '1 000' → Decimal('1000').
    Returns None when the input is not a finite number.
    """
    cleaned = raw.strip().replace(",", ".").replace(" ", "")
    if not cleaned:
        return None
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def _parse_search_query(raw: str) -> str:
    """Normalize a search query to a bare username or app_id.

    Accepts '@username', 'username', 't.me/username' and
    'https://t.me/username' links as well as numeric ids, returning the bare
    token with no '@', URL prefix or trailing slash.
    """
    token = raw.strip()
    if not token:
        return ""
    lowered = token.lower()
    for prefix in ("https://", "http://"):
        if lowered.startswith(prefix):
            token = token[len(prefix):]
            lowered = token.lower()
            break
    for prefix in ("t.me/", "telegram.me/"):
        if lowered.startswith(prefix):
            token = token[len(prefix):]
            break
    token = token.strip("/").lstrip("@")
    return token.split("/")[0].split("?")[0].strip()


async def _show_deposit_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Edit the current message into the 'enter amount' prompt and arm the state.

    The prompt's message id is remembered so the later text-input handler can
    edit this very message (keeping the flow inside one message)."""
    await state.set_state(WalletStates.awaiting_deposit_amount)
    await state.update_data(
        prompt_chat_id=callback.message.chat.id,
        prompt_message_id=callback.message.message_id,
        invoice_id=None,
    )
    await _edit_section(
        callback,
        texts.deposit_prompt(settings.deposit_commission_percent),
        keyboards.deposit_back(),
    )


async def _show_withdraw_prompt(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Edit the current message into the 'enter withdrawal amount' prompt (showing
    the available balance) and arm the state. The prompt's message id is remembered
    so the later text-input handler can edit this same message."""
    user = await UserService(session).get_by_telegram_id(callback.from_user.id)
    available = user.deposit if user is not None else Decimal("0")
    await state.set_state(WalletStates.awaiting_withdraw_amount)
    await state.update_data(
        prompt_chat_id=callback.message.chat.id,
        prompt_message_id=callback.message.message_id,
    )
    await _edit_section(
        callback,
        texts.withdraw_prompt(available, settings.withdraw_commission_percent),
        keyboards.withdraw_back(),
    )


def _cancel_watcher(tg_id: int) -> None:
    task = _watchers.pop(tg_id, None)
    if task is not None:
        task.cancel()


async def _deal_link(bot: Bot, token: str) -> str:
    """Build the deep-link a partner follows to join the deal."""
    me = await bot.me()
    return f"https://t.me/{me.username}?start=deal_{token}"


def _deal_buyer(deal) -> User | None:
    """The participant who pays for the deal — always the buyer.

    The owner is the buyer when ``owner_role == 'buyer'``; otherwise the partner
    is. ``deal`` must have owner/partner eagerly loaded (``get_with_users``)."""
    return deal.owner if deal.owner_role == "buyer" else deal.partner


def _deal_seller(deal) -> User | None:
    """The participant who receives the funds — always the seller (the opposite
    of :func:`_deal_buyer`). Needs owner/partner eagerly loaded."""
    return deal.partner if deal.owner_role == "buyer" else deal.owner


async def _show_deal_live(
    callback: CallbackQuery, bot: Bot, deal, viewer_tg_id: int, *, page: int = 1
) -> None:
    """Render the unified 'Мои сделки' deal card for the message being edited.

    The same layout is used for every status (:func:`texts.deal_card`); only the
    action buttons differ by status and the viewer's role
    (:func:`keyboards.my_deal_actions`). This is the single management surface — used
    both when opening a deal from the list and when returning to it from a sub-screen
    (pay/dispute/receipt/cancel confirmations). ``deal`` must have owner/partner eagerly
    loaded. ``page`` is the list page the 'Назад' button returns to."""
    buyer = _deal_buyer(deal)
    is_buyer = buyer is not None and buyer.tg_id == viewer_tg_id
    viewer_role = "buyer" if is_buyer else "seller"
    link = await _deal_link(bot, deal.token) if deal.status == "active" else None
    await _edit_section(
        callback,
        texts.deal_card(
            number=deal.number,
            viewer_role=viewer_role,
            amount=deal.amount,
            status=deal.status,
            terms=deal.terms,
        ),
        keyboards.my_deal_actions(
            deal_id=deal.id, status=deal.status, is_buyer=is_buyer, page=page, link=link
        ),
    )


async def _expire_one(bot: Bot, service: DealService, deal) -> None:
    """Mark a deal expired and notify the owner with the 'expired' notice.

    The notice is a fresh message to the owner's private chat (``owner.tg_id``);
    the original invite is left as-is — joining it is already blocked once the
    deal is no longer active."""
    owner = deal.owner
    await service.expire(deal)
    with suppress(TelegramBadRequest):
        await bot.send_message(
            owner.tg_id,
            texts.deal_expired(
                number=deal.number,
                owner_role=deal.owner_role,
                username=owner.username,
                app_id=owner.app_id,
                amount=deal.amount,
                created_at=deal.created_at,
                terms=deal.terms,
            ),
            reply_markup=keyboards.back_to_menu(),
        )


async def _expire_sweeper(bot: Bot) -> None:
    """Restart-safe expiry: scan the DB for overdue active deals and close them.

    Rebuilds its work purely from the DB each tick (the ``expires_at`` column is
    the source of truth), so pending expirations survive a restart. Runs for the
    lifetime of the bot."""
    while True:
        try:
            async with session_factory() as session:
                service = DealService(session)
                for deal in await service.list_expired():
                    await _expire_one(bot, service, deal)
        except Exception:
            logger.exception("deal expiry sweeper iteration failed")
        await asyncio.sleep(_SWEEP_INTERVAL)


def start_background_tasks(bot: Bot) -> None:
    """Launch long-lived background loops. Call once, inside the running loop."""
    asyncio.create_task(_expire_sweeper(bot))


async def _join_deal(
    message: Message, session: AsyncSession, user: User, token: str
) -> None:
    """Handle a partner following an invite deep-link (?start=deal_<token>)."""
    service = DealService(session)
    deal = await service.get_by_token(token)

    if deal is None:
        await message.answer(texts.DEAL_NOT_FOUND, reply_markup=keyboards.back_to_menu())
        return
    if (
        deal.status == "active"
        and deal.expires_at is not None
        and deal.expires_at <= datetime.now(timezone.utc)
    ):
        await _expire_one(message.bot, service, deal)
        await message.answer(
            texts.DEAL_INVITE_EXPIRED, reply_markup=keyboards.back_to_menu()
        )
        return
    if deal.owner_id == user.id:
        await message.answer(texts.DEAL_SELF_JOIN, reply_markup=keyboards.back_to_menu())
        return
    if deal.partner_id == user.id:
        await message.answer(
            texts.DEAL_ALREADY_JOINED, reply_markup=keyboards.back_to_menu()
        )
        return
    if deal.partner_id is not None:
        await message.answer(texts.DEAL_TAKEN, reply_markup=keyboards.back_to_menu())
        return
    if deal.status != "active":
        await message.answer(
            texts.DEAL_INVITE_EXPIRED, reply_markup=keyboards.back_to_menu()
        )
        return

    partner_role = OPPOSITE_ROLE.get(deal.owner_role, deal.owner_role)
    await message.answer(
        texts.deal_offer(
            number=deal.number,
            partner_role=partner_role,
            amount=deal.amount,
            terms=deal.terms,
        ),
        reply_markup=keyboards.deal_offer(deal.id),
    )


async def _credit_deposit(
    tg_id: int,
    amount: Decimal,
    *,
    commission_percent: Decimal,
    commission_amount: Decimal,
) -> Decimal:
    """Add ``amount`` to the user's balance, record the (paid) deposit in the
    transactions table atomically, and return the new balance."""
    async with session_factory() as session:
        user = await UserService(session).get_by_telegram_id(tg_id)
        if user is None:
            return Decimal("0")
        user.deposit = user.deposit + amount
        TransactionService(session).add_deposit(
            user_id=user.id,
            amount=amount,
            commission_percent=commission_percent,
            commission_amount=commission_amount,
        )
        await session.commit()
        return user.deposit


async def _watch_invoice(
    bot: Bot,
    chat_id: int,
    message_id: int,
    tg_id: int,
    invoice_id: int,
    credit: Decimal,
    commission: Decimal,
    pct: Decimal,
) -> None:
    """Poll an invoice until it's paid or the 5-minute window elapses."""
    deadline = time.monotonic() + _INVOICE_TTL
    try:
        while time.monotonic() < deadline:
            await asyncio.sleep(_POLL_INTERVAL)
            try:
                invoice = await crypto_pay.get_invoice(invoice_id)
            except crypto_pay.CryptoPayError as exc:
                logger.warning("Polling invoice %s failed: %s", invoice_id, exc)
                continue
            if invoice is not None and invoice.is_paid:
                balance = await _credit_deposit(
                    tg_id,
                    credit,
                    commission_percent=pct,
                    commission_amount=commission,
                )
                with suppress(TelegramBadRequest):
                    await bot.edit_message_text(
                        texts.deposit_success(credit, balance),
                        chat_id=chat_id,
                        message_id=message_id,
                        reply_markup=keyboards.deposit_success(),
                    )
                return
        await crypto_pay.delete_invoice(invoice_id)
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                texts.DEPOSIT_INVOICE_EXPIRED,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboards.deposit_expired(),
            )
    finally:
        _watchers.pop(tg_id, None)


@router.message(CommandStart())
async def cmd_start(
    message: Message, command: CommandObject, session: AsyncSession, state: FSMContext
) -> None:
    _cancel_watcher(message.from_user.id)
    await state.clear()
    user, _ = await UserService(session).get_or_create(message.from_user)

    payload = command.args or ""
    if payload.startswith("deal_"):
        await _join_deal(message, session, user, payload[len("deal_"):])
        return

    await message.answer(texts.MAIN_MENU, reply_markup=keyboards.main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP)


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _edit_section(callback, texts.MAIN_MENU, keyboards.main_menu())


@router.callback_query(F.data == "menu:autogarant")
async def cb_autogarant(callback: CallbackQuery) -> None:
    await _edit_section(callback, texts.AUTOGARANT_SECTION, keyboards.autogarant_menu())


@router.callback_query(F.data == "autogarant:create")
async def cb_create_deal(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _edit_section(callback, texts.CREATE_DEAL_ROLE, keyboards.create_deal_role())


@router.callback_query(F.data == "deal:role:buyer")
@router.callback_query(F.data == "deal:role:seller")
async def cb_deal_role(callback: CallbackQuery, state: FSMContext) -> None:
    """Role chosen (buyer/seller) — ask for the deal amount in USDT.

    Both roles share the identical single-message flow; only the stored
    ``deal_role`` differs, which later drives the role label on the confirm
    screen (:func:`on_deal_terms`) and the partner's opposite role on the
    invite (:func:`cb_deal_confirm`)."""
    role = "seller" if callback.data == "deal:role:seller" else "buyer"
    await state.set_state(DealStates.awaiting_amount)
    await state.update_data(
        prompt_chat_id=callback.message.chat.id,
        prompt_message_id=callback.message.message_id,
        deal_role=role,
    )
    await _edit_section(callback, texts.DEAL_AMOUNT_PROMPT, keyboards.deal_amount_back())


@router.message(DealStates.awaiting_amount)
async def on_deal_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    amount = _parse_amount(message.text or "")
    with suppress(TelegramBadRequest):
        await message.delete()

    data = await state.get_data()
    chat_id = data.get("prompt_chat_id", message.chat.id)
    message_id = data.get("prompt_message_id")
    if message_id is None:
        return

    async def _show(text: str, markup) -> None:
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id, reply_markup=markup
            )

    if amount is None or amount <= 0:
        await _show(texts.DEAL_AMOUNT_INVALID, keyboards.deal_amount_back())
        return

    deal_amount = amount.quantize(_CENTS, rounding=ROUND_HALF_UP)
    if deal_amount < _DEAL_MIN:
        await _show(texts.DEAL_BELOW_MIN, keyboards.deal_amount_back())
        return

    await state.update_data(deal_amount=str(deal_amount))
    await state.set_state(DealStates.awaiting_terms)
    await _show(texts.DEAL_TERMS_PROMPT, keyboards.deal_terms_back())


@router.message(DealStates.awaiting_terms)
async def on_deal_terms(message: Message, state: FSMContext, bot: Bot) -> None:
    terms = (message.text or "").strip()
    with suppress(TelegramBadRequest):
        await message.delete()

    data = await state.get_data()
    chat_id = data.get("prompt_chat_id", message.chat.id)
    message_id = data.get("prompt_message_id")
    if message_id is None:
        return

    async def _show(text: str, markup) -> None:
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id, reply_markup=markup
            )

    if not terms:
        await _show(texts.DEAL_TERMS_PROMPT, keyboards.deal_terms_back())
        return

    deal_amount = Decimal(data.get("deal_amount", "0"))
    role = data.get("deal_role", "buyer")
    await state.update_data(deal_terms=terms)
    await state.set_state(DealStates.awaiting_confirm)
    await _show(
        texts.deal_confirm(
            role_label=texts.ROLE_LABELS.get(role, role),
            amount=deal_amount,
            pay_amount=deal_amount,
            terms=terms,
        ),
        keyboards.deal_confirm(),
    )


@router.callback_query(F.data == "deal:confirm")
async def cb_deal_confirm(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    """Persist the deal, swap the section into the 'created' notice and send the
    forwardable invite, then arm the 15-minute expiry timer."""
    data = await state.get_data()
    role = data.get("deal_role")
    amount_raw = data.get("deal_amount")
    terms = data.get("deal_terms")
    if not role or amount_raw is None or not terms:
        await callback.answer("Сессия истекла, начните заново", show_alert=True)
        return

    amount = Decimal(amount_raw)
    user = await UserService(session).get_by_telegram_id(callback.from_user.id)
    service = DealService(session)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_DEAL_TTL)
    deal = await service.create(
        owner_id=user.id,
        owner_role=role,
        amount=amount,
        terms=terms,
        expires_at=expires_at,
    )
    await state.clear()

    await callback.message.edit_text(
        texts.deal_created(deal.number), reply_markup=keyboards.deal_created()
    )
    await callback.answer()

    partner_role = OPPOSITE_ROLE.get(role, role)
    link = await _deal_link(bot, deal.token)
    await callback.message.answer(
        texts.deal_invite(number=deal.number, partner_role=partner_role, amount=amount),
        reply_markup=keyboards.deal_invite_link(link),
    )


@router.callback_query(F.data.startswith("deal:accept:"))
async def cb_deal_accept(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    """Partner accepts the offer: lock the deal in (status→accepted, partner_id),
    confirm to the partner, and prompt the owner for payment."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    user = await UserService(session).get_by_telegram_id(callback.from_user.id)

    async def _close(text: str) -> None:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(text, reply_markup=keyboards.back_to_menu())
        await callback.answer()

    if deal is None:
        await _close(texts.DEAL_NOT_FOUND)
        return
    if (
        deal.status == "active"
        and deal.expires_at is not None
        and deal.expires_at <= datetime.now(timezone.utc)
    ):
        await _expire_one(bot, service, deal)
        await _close(texts.DEAL_INVITE_EXPIRED)
        return
    if deal.owner_id == user.id:
        await _close(texts.DEAL_SELF_JOIN)
        return
    if deal.partner_id is not None and deal.partner_id != user.id:
        await _close(texts.DEAL_TAKEN)
        return
    if deal.status != "active":
        await _close(texts.DEAL_INVITE_EXPIRED)
        return

    await service.accept(deal, partner_id=user.id)
    deal = await service.get_with_users(deal_id)
    owner, partner = deal.owner, deal.partner

    buyer, seller = _deal_buyer(deal), _deal_seller(deal)
    actor_is_buyer = buyer is not None and buyer.tg_id == callback.from_user.id

    accepted_card = texts.deal_accepted(
        number=deal.number,
        owner_role=deal.owner_role,
        owner_username=owner.username,
        owner_app_id=owner.app_id,
        partner_username=partner.username,
        partner_app_id=partner.app_id,
        amount=deal.amount,
        terms=deal.terms,
    )
    payment_card = texts.deal_payment_request(
        number=deal.number,
        amount=deal.amount,
        terms=deal.terms,
        balance=buyer.deposit if buyer is not None else Decimal("0"),
    )

    await callback.answer()
    if actor_is_buyer:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(
                payment_card, reply_markup=keyboards.deal_payment(deal.id)
            )
        if seller is not None:
            with suppress(TelegramBadRequest):
                await bot.send_message(
                    seller.tg_id,
                    texts.deal_accepted_seller(
                        number=deal.number,
                        owner_role=deal.owner_role,
                        owner_username=owner.username,
                        owner_app_id=owner.app_id,
                        partner_username=partner.username,
                        partner_app_id=partner.app_id,
                        amount=deal.amount,
                        terms=deal.terms,
                    ),
                )
    else:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(accepted_card)
        if buyer is not None:
            with suppress(TelegramBadRequest):
                await bot.send_message(
                    buyer.tg_id,
                    payment_card,
                    reply_markup=keyboards.deal_payment(deal.id),
                )


@router.callback_query(F.data.startswith("deal:reject:"))
async def cb_deal_reject(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    """Partner declines the offer: cancel the deal (status→cancelled), show the
    'cancelled' card to the partner, and notify the owner."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    user = await UserService(session).get_by_telegram_id(callback.from_user.id)

    async def _close(text: str) -> None:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(text, reply_markup=keyboards.back_to_menu())
        await callback.answer()

    if deal is None:
        await _close(texts.DEAL_NOT_FOUND)
        return
    if deal.owner_id == user.id:
        await _close(texts.DEAL_SELF_JOIN)
        return
    if deal.partner_id is not None and deal.partner_id != user.id:
        await _close(texts.DEAL_TAKEN)
        return
    if deal.status != "active":
        await _close(texts.DEAL_INVITE_EXPIRED)
        return

    owner = deal.owner
    await service.cancel(deal)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            texts.deal_cancelled(
                number=deal.number,
                owner_role=deal.owner_role,
                owner_username=owner.username,
                owner_app_id=owner.app_id,
                partner_username=user.username,
                partner_app_id=user.app_id,
                amount=deal.amount,
                terms=deal.terms,
            )
        )
    await callback.answer()

    with suppress(TelegramBadRequest):
        await bot.send_message(
            owner.tg_id,
            texts.deal_rejected_by_partner(deal.number),
            reply_markup=keyboards.back_to_menu(),
        )


@router.callback_query(F.data.startswith("deal:pay:"))
async def cb_deal_pay(callback: CallbackQuery, session: AsyncSession) -> None:
    """Buyer pays from balance. Picks the buyer's deposit (owner or partner,
    depending on ``owner_role``); if it can't cover the amount, swaps the message
    into the 'insufficient funds' screen, otherwise asks for confirmation before
    the funds are debited into escrow (``deal:payconfirm``)."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status != "accepted":
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    buyer = _deal_buyer(deal)
    balance = buyer.deposit if buyer is not None else Decimal("0")
    if balance < deal.amount:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(
                texts.deal_insufficient(need=deal.amount, available=balance),
                reply_markup=keyboards.deal_insufficient(deal.id),
            )
        await callback.answer()
        return

    await _edit_section(
        callback,
        texts.deal_pay_confirm(number=deal.number, amount=deal.amount),
        keyboards.deal_pay_confirm(deal.id),
    )


@router.callback_query(F.data.startswith("deal:payconfirm:"))
@router.callback_query(F.data.startswith("deal:paycancel:"))
async def cb_deal_pay_decision(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status != "accepted":
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    if callback.data.startswith("deal:paycancel:"):
        await _show_deal_live(callback, bot, deal, callback.from_user.id)
        return

    buyer = _deal_buyer(deal)
    balance = buyer.deposit if buyer is not None else Decimal("0")
    if buyer is None or balance < deal.amount:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(
                texts.deal_insufficient(need=deal.amount, available=balance),
                reply_markup=keyboards.deal_insufficient(deal.id),
            )
        await callback.answer()
        return

    await service.pay(deal, buyer)
    await _show_deal_live(callback, bot, deal, callback.from_user.id)

    seller = _deal_seller(deal)
    if seller is not None:
        with suppress(TelegramBadRequest):
            await bot.send_message(
                seller.tg_id,
                texts.deal_seller_escrow(
                    number=deal.number, amount=deal.amount, terms=deal.terms
                ),
                reply_markup=keyboards.back_to_menu(),
            )


@router.callback_query(F.data.startswith("deal:dispute:"))
async def cb_deal_dispute(callback: CallbackQuery, session: AsyncSession) -> None:
    """Buyer taps '⚠️ Открыть спор' on the escrow card: ask for confirmation.
    '⬅️ Назад' returns to the escrow card via ``deal:back``."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status != "escrow":
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    await _edit_section(
        callback,
        texts.deal_dispute_confirm(deal.number),
        keyboards.deal_dispute_confirm(deal.id),
    )


@router.callback_query(F.data.startswith("deal:disputeconfirm:"))
async def cb_deal_dispute_confirm(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status != "escrow":
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    owner, partner = deal.owner, deal.partner
    await service.open_dispute(deal)

    await _edit_section(
        callback, texts.deal_dispute_opened(deal.number), keyboards.back_to_menu()
    )

    other = partner if owner and owner.tg_id == callback.from_user.id else owner
    if other is not None:
        with suppress(TelegramBadRequest):
            await bot.send_message(
                other.tg_id,
                texts.deal_dispute_opened_partner(deal.number),
                reply_markup=keyboards.back_to_menu(),
            )

    card = texts.deal_dispute_admin(
        number=deal.number,
        owner_role=deal.owner_role,
        owner_username=owner.username,
        owner_app_id=owner.app_id,
        partner_username=partner.username if partner else None,
        partner_app_id=partner.app_id if partner else None,
        amount=deal.amount,
        terms=deal.terms,
    )
    if not settings.admin_id_list:
        logger.warning("Dispute opened on deal #%s but no admins configured", deal.number)
    for admin_id in settings.admin_id_list:
        with suppress(TelegramBadRequest):
            await bot.send_message(
                admin_id, card, reply_markup=keyboards.dispute_admin_close(deal.id)
            )


@router.callback_query(F.data.startswith("dispute:close:"))
async def cb_dispute_close(callback: CallbackQuery, session: AsyncSession) -> None:
    """Admin taps '🔒 Закрыть спор': edit their notice into the 'which side?' prompt
    with the buyer/seller buttons. Final resolution is ``dispute:resolve:…``."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status != "dispute":
        await callback.answer("Спор больше не активен", show_alert=True)
        return

    await _edit_section(
        callback,
        texts.deal_dispute_resolve_prompt(deal.number),
        keyboards.dispute_admin_resolve(deal.id),
    )


@router.callback_query(F.data.startswith("dispute:back:"))
async def cb_dispute_back(callback: CallbackQuery, session: AsyncSession) -> None:
    """Admin taps '⬅️ Назад' on the 'which side?' prompt: re-render the dispute card
    (with '🔒 Закрыть спор') so they can re-read the deal before deciding."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status != "dispute":
        await callback.answer("Спор больше не активен", show_alert=True)
        return

    await _edit_section(
        callback,
        texts.deal_dispute_admin(
            number=deal.number,
            owner_role=deal.owner_role,
            owner_username=deal.owner.username,
            owner_app_id=deal.owner.app_id,
            partner_username=deal.partner.username if deal.partner else None,
            partner_app_id=deal.partner.app_id if deal.partner else None,
            amount=deal.amount,
            terms=deal.terms,
        ),
        keyboards.dispute_admin_close(deal.id),
    )


@router.callback_query(F.data.startswith("dispute:resolve:"))
async def cb_dispute_resolve(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    """Admin picks the winning side ('🛒 Покупатель' / '💼 Продавец'): hand the held
    escrow funds to that side (seller → release, buyer → refund), close the deal,
    confirm on the admin's message and notify both participants of the outcome."""
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer()
        return
    winner_role = parts[2]
    try:
        deal_id = int(parts[3])
    except ValueError:
        await callback.answer()
        return
    if winner_role not in ("buyer", "seller"):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status != "dispute":
        await callback.answer("Спор больше не активен", show_alert=True)
        return

    buyer, seller = _deal_buyer(deal), _deal_seller(deal)
    if buyer is None or seller is None:
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    amount = deal.amount
    winner, loser = (seller, buyer) if winner_role == "seller" else (buyer, seller)
    loser_role = "buyer" if winner_role == "seller" else "seller"
    result_status = "completed" if winner_role == "seller" else "cancelled"
    await service.resolve_dispute(deal, recipient=winner, status=result_status)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            texts.deal_dispute_resolved_admin(number=deal.number, winner_role=winner_role)
        )
    await callback.answer()

    footer = (
        {"credited": amount} if winner_role == "seller" else {"refunded": amount}
    )
    with suppress(TelegramBadRequest):
        await bot.send_message(
            winner.tg_id,
            texts.deal_dispute_result(
                number=deal.number,
                role=winner_role,
                decision=winner_role,
                amount=amount,
                terms=deal.terms,
                balance=winner.deposit,
                **footer,
            ),
            reply_markup=keyboards.deal_completed(),
        )
    with suppress(TelegramBadRequest):
        await bot.send_message(
            loser.tg_id,
            texts.deal_dispute_result(
                number=deal.number,
                role=loser_role,
                decision=winner_role,
                amount=amount,
                terms=deal.terms,
            ),
            reply_markup=keyboards.back_to_menu(),
        )


@router.callback_query(F.data.startswith("deal:receipt:"))
async def cb_deal_receipt(callback: CallbackQuery, session: AsyncSession) -> None:
    """Buyer taps '✅ Подтвердить получение' on the escrow card: show the confirm
    screen before releasing the funds to the seller (confirm logic built next).
    '⬅️ Назад' returns to the escrow card via ``deal:back``."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status != "escrow":
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    await _edit_section(
        callback,
        texts.deal_receipt_confirm(
            number=deal.number,
            owner_role=deal.owner_role,
            amount=deal.amount,
            terms=deal.terms,
            status=deal.status,
        ),
        keyboards.deal_receipt_confirm(deal.id),
    )


@router.callback_query(F.data.startswith("deal:receiptconfirm:"))
async def cb_deal_receipt_confirm(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status != "escrow":
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    seller = _deal_seller(deal)
    if seller is None:
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    amount = deal.amount
    await service.complete(deal, seller)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            texts.deal_completed(
                number=deal.number,
                role="buyer",
                amount=deal.amount,
                terms=deal.terms,
            )
        )
    await callback.answer()

    with suppress(TelegramBadRequest):
        await bot.send_message(
            seller.tg_id,
            texts.deal_completed(
                number=deal.number,
                role="seller",
                amount=deal.amount,
                terms=deal.terms,
                credited=amount,
                balance=seller.deposit,
            ),
            reply_markup=keyboards.deal_completed(),
        )


@router.callback_query(F.data.startswith("deal:back:"))
async def cb_deal_back(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    """Return to the live deal card. Used by 'Назад' from the insufficient-funds and
    confirmation sub-screens, 'Нет' on the cancel-request screens, and 'Вернуться к
    сделке' after a declined cancel."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status not in ("active", "accepted", "escrow"):
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    await _show_deal_live(callback, bot, deal, callback.from_user.id)


@router.callback_query(F.data.startswith("deal:cancelactive:"))
async def cb_deal_cancel_active(callback: CallbackQuery, session: AsyncSession) -> None:
    """Owner asks to cancel a not-yet-accepted ('active') deal: show the confirmation.
    No partner has joined, so it's cancelled immediately on confirm (no consent,
    nothing to refund). '❌ Нет' returns to the card via ``deal:back``."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status != "active":
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    await _edit_section(
        callback,
        texts.deal_cancel_active_confirm(deal.number),
        keyboards.deal_cancel_active_confirm(deal.id),
    )


@router.callback_query(F.data.startswith("deal:cancelactiveok:"))
async def cb_deal_cancel_active_confirm(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    """Owner confirmed cancelling an 'active' deal — close it for good and re-render
    the (now cancelled) card."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status != "active":
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    await service.cancel(deal)
    await _show_deal_live(callback, bot, deal, callback.from_user.id)


@router.callback_query(F.data.startswith("deal:cancel:"))
async def cb_deal_cancel(callback: CallbackQuery, session: AsyncSession) -> None:
    """Owner asks to cancel: show the confirmation screen. Works from both the
    payment prompt (accepted) and the escrow card (paid) — the status line reflects
    which. Cancellation is only a *request* that needs the other side's consent
    (the '✅ Да' button → ``deal:cancelreq``). '❌ Нет' returns to the deal."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status not in ("accepted", "escrow"):
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    await _edit_section(
        callback,
        texts.deal_cancel_request(
            number=deal.number,
            owner_role=deal.owner_role,
            amount=deal.amount,
            terms=deal.terms,
            status=deal.status,
        ),
        keyboards.deal_cancel_confirm(deal.id),
    )


@router.callback_query(F.data.startswith("deal:cancelreq:"))
async def cb_deal_cancel_request(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    """Owner confirmed '✅ Да, запросить отмену': mark the owner's screen as awaiting
    cancellation and ask the partner to agree or decline. The actual execution of
    the request (withdraw / agree / decline) is built later."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status not in ("accepted", "escrow"):
        await callback.answer("Сделка больше недоступна", show_alert=True)
        return

    owner, partner = deal.owner, deal.partner
    await service.request_cancel(deal)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            texts.deal_cancel_pending(
                number=deal.number,
                owner_role=deal.owner_role,
                amount=deal.amount,
                terms=deal.terms,
                status=deal.status,
            ),
            reply_markup=keyboards.deal_cancel_withdraw(deal.id),
        )
    await callback.answer("Запрос отправлен. Ждём согласия партнёра.", show_alert=True)

    if partner is not None:
        sent = None
        with suppress(TelegramBadRequest):
            sent = await bot.send_message(
                partner.tg_id,
                texts.deal_cancel_requested_partner(
                    number=deal.number,
                    owner_role=deal.owner_role,
                    owner_username=owner.username,
                    owner_app_id=owner.app_id,
                    partner_username=partner.username,
                    partner_app_id=partner.app_id,
                    amount=deal.amount,
                    terms=deal.terms,
                ),
                reply_markup=keyboards.deal_cancel_decision(deal.id),
            )
        if sent is not None:
            await service.set_cancel_request_message(deal, sent.message_id)


@router.callback_query(F.data.startswith("deal:cancelwithdraw:"))
async def cb_deal_cancel_withdraw(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    """Owner withdraws a pending cancel request: back to 'accepted', return the
    owner to the payment screen and clear the partner's request message."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status not in _CANCEL_PENDING:
        await callback.answer("Запрос больше не активен", show_alert=True)
        return

    partner = deal.partner
    request_msg_id = deal.cancel_request_msg_id
    await service.revert_cancel(deal)

    await _show_deal_live(callback, bot, deal, callback.from_user.id)
    await callback.answer("Запрос на отмену отозван.", show_alert=True)

    if partner is not None and request_msg_id is not None:
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                texts.DEAL_CANCEL_WITHDRAWN,
                chat_id=partner.tg_id,
                message_id=request_msg_id,
            )


@router.callback_query(F.data.startswith("deal:cancelagree:"))
async def cb_deal_cancel_agree(callback: CallbackQuery, session: AsyncSession) -> None:
    """Partner taps '✅ Согласиться': show the confirm-before-agreeing screen on the
    partner's own message. Final execution is the '✅ Да, отменить' button (later)."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status not in _CANCEL_PENDING:
        await callback.answer("Запрос больше не активен", show_alert=True)
        return

    partner_role = OPPOSITE_ROLE.get(deal.owner_role, deal.owner_role)
    await _edit_section(
        callback,
        texts.deal_cancel_confirm_partner(
            number=deal.number,
            partner_role=partner_role,
            amount=deal.amount,
            terms=deal.terms,
            status=deal.status,
        ),
        keyboards.deal_cancel_agree_confirm(deal.id),
    )


@router.callback_query(F.data.startswith("deal:canceldecline:"))
async def cb_deal_cancel_decline(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    """Partner declines the cancellation — used by both '❌ Отклонить' and the
    confirm screen's '❌ Нет'. Reverts the deal to 'accepted' and tells the owner,
    who can jump back to the live deal."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status not in _CANCEL_PENDING:
        await callback.answer("Запрос больше не активен", show_alert=True)
        return

    owner = deal.owner
    await service.revert_cancel(deal)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            texts.deal_cancel_declined_partner(deal.number)
        )
    await callback.answer()

    with suppress(TelegramBadRequest):
        await bot.send_message(
            owner.tg_id,
            texts.deal_cancel_declined_owner(
                number=deal.number, amount=deal.amount, terms=deal.terms
            ),
            reply_markup=keyboards.deal_return(deal.id),
        )


@router.callback_query(F.data.startswith("deal:cancelconfirm:"))
async def cb_deal_cancel_confirm(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    """Partner confirms '✅ Да, отменить': cancel the deal for good and show the
    'cancelled' card to both sides (buyer/seller follow ``owner_role`` from the DB,
    the partner being the opposite role). An escrow cancel refunds the buyer and
    shows the mutual-consent card with a refund footer on the buyer's copy."""
    try:
        deal_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return

    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or deal.status not in _CANCEL_PENDING:
        await callback.answer("Запрос больше не активен", show_alert=True)
        return

    owner, partner = deal.owner, deal.partner
    was_escrow = deal.status == "escrow_cancel"
    buyer = _deal_buyer(deal) if was_escrow else None
    amount = deal.amount
    await service.cancel(deal, refund_to=buyer)

    if not was_escrow:
        card = texts.deal_cancelled(
            number=deal.number,
            owner_role=deal.owner_role,
            owner_username=owner.username,
            owner_app_id=owner.app_id,
            partner_username=partner.username if partner else None,
            partner_app_id=partner.app_id if partner else None,
            amount=deal.amount,
            terms=deal.terms,
        )
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(card)
        await callback.answer()
        with suppress(TelegramBadRequest):
            await bot.send_message(owner.tg_id, card)
        return

    new_balance = buyer.deposit if buyer is not None else None
    owner_is_buyer = deal.owner_role == "buyer"

    def _card(*, with_footer: bool) -> str:
        return texts.deal_cancelled_escrow(
            number=deal.number,
            owner_role=deal.owner_role,
            owner_username=owner.username,
            owner_app_id=owner.app_id,
            partner_username=partner.username if partner else None,
            partner_app_id=partner.app_id if partner else None,
            amount=deal.amount,
            terms=deal.terms,
            refunded=amount if with_footer else None,
            balance=new_balance if with_footer else None,
        )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(_card(with_footer=not owner_is_buyer))
    await callback.answer()
    with suppress(TelegramBadRequest):
        await bot.send_message(owner.tg_id, _card(with_footer=owner_is_buyer))


@router.callback_query(F.data == "menu:search")
async def cb_search(callback: CallbackQuery, state: FSMContext) -> None:
    """Open the 'Поиск' section: prompt for a username/id and arm the state so the
    next text message is treated as a lookup query (edited into this same message)."""
    await state.set_state(SearchStates.awaiting_query)
    await state.update_data(
        prompt_chat_id=callback.message.chat.id,
        prompt_message_id=callback.message.message_id,
    )
    await _edit_section(callback, texts.SEARCH_SECTION, keyboards.back_to_menu())


@router.callback_query(F.data == "menu:profile")
async def cb_profile(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await UserService(session).get_by_telegram_id(callback.from_user.id)
    text = texts.profile(
        username=user.username,
        app_id=user.app_id,
        deposit=user.deposit,
        deposit_rub=await _deposit_in_rub(user.deposit),
        registered_at=user.registered_at,
    )
    await _edit_section(callback, text, keyboards.profile_menu())


@router.callback_query(F.data.startswith("mydeals:page:"))
async def cb_my_deals(callback: CallbackQuery, session: AsyncSession) -> None:
    """Render a page of the user's deals (owner or partner), 5 per page, newest
    first. Each deal is a button; navigation is a Назад/Вперёд row plus a return to
    the profile. Also the landing handler for the profile's 'Мои сделки' button."""
    try:
        page = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer()
        return
    page = max(1, page)

    user = await UserService(session).get_by_telegram_id(callback.from_user.id)
    service = DealService(session)
    total = await service.count_for_user(user.id)
    if total == 0:
        await _edit_section(callback, texts.MY_DEALS_EMPTY, keyboards.my_deals_empty())
        return

    total_pages = (total + _DEALS_PER_PAGE - 1) // _DEALS_PER_PAGE
    page = min(page, total_pages)
    deals = await service.list_for_user(
        user.id, offset=(page - 1) * _DEALS_PER_PAGE, limit=_DEALS_PER_PAGE
    )
    items = [
        (d.id, texts.deal_button_label(number=d.number, amount=d.amount, status=d.status))
        for d in deals
    ]
    await _edit_section(
        callback,
        texts.my_deals(page=page, total_pages=total_pages),
        keyboards.my_deals(deals=items, page=page, total_pages=total_pages),
    )


@router.callback_query(F.data.startswith("mydeals:open:"))
async def cb_my_deal_open(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    """Open a deal from 'Мои сделки' as its unified live card. The single management
    surface: every status renders the same card layout (:func:`texts.deal_card`); the
    action buttons differ by status and the viewer's role
    (:func:`keyboards.my_deal_actions` via :func:`_show_deal_live`). Terminal and
    dispute statuses expose only 'Назад'. Each action handler re-checks the status, so
    a stale pushed copy of the deal stays harmless."""
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer()
        return
    try:
        deal_id, page = int(parts[2]), int(parts[3])
    except ValueError:
        await callback.answer()
        return

    user = await UserService(session).get_by_telegram_id(callback.from_user.id)
    service = DealService(session)
    deal = await service.get_with_users(deal_id)
    if deal is None or user.id not in (deal.owner_id, deal.partner_id):
        await callback.answer("Сделка недоступна", show_alert=True)
        return

    await _show_deal_live(callback, bot, deal, callback.from_user.id, page=page)


@router.callback_query(F.data == "menu:wallet")
async def cb_wallet(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    _cancel_watcher(callback.from_user.id)
    await state.clear()
    user = await UserService(session).get_by_telegram_id(callback.from_user.id)
    text = texts.wallet(
        deposit=user.deposit,
        deposit_rub=await _deposit_in_rub(user.deposit),
        deposit_commission_percent=settings.deposit_commission_percent,
        withdraw_commission_percent=settings.withdraw_commission_percent,
    )
    await _edit_section(callback, text, keyboards.wallet_menu())


@router.callback_query(F.data == "wallet:deposit")
async def cb_wallet_deposit(callback: CallbackQuery, state: FSMContext) -> None:
    _cancel_watcher(callback.from_user.id)
    await _show_deposit_prompt(callback, state)


@router.callback_query(F.data == "deposit:cancel")
async def cb_deposit_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel a pending invoice: stop the timer, delete it, return to the prompt."""
    _cancel_watcher(callback.from_user.id)
    data = await state.get_data()
    invoice_id = data.get("invoice_id")
    if invoice_id is not None:
        await crypto_pay.delete_invoice(invoice_id)
    await _show_deposit_prompt(callback, state)


@router.message(WalletStates.awaiting_deposit_amount)
async def on_deposit_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    amount = _parse_amount(message.text or "")
    with suppress(TelegramBadRequest):
        await message.delete()

    data = await state.get_data()
    chat_id = data.get("prompt_chat_id", message.chat.id)
    message_id = data.get("prompt_message_id")
    if message_id is None:
        return

    async def _show(text: str, markup) -> None:
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id, reply_markup=markup
            )

    if amount is None or amount <= 0:
        await _show(texts.DEPOSIT_INVALID, keyboards.deposit_back())
        return

    credit = amount.quantize(_CENTS, rounding=ROUND_HALF_UP)
    if credit < _DEPOSIT_MIN:
        await _show(texts.DEPOSIT_BELOW_MIN, keyboards.deposit_back())
        return

    pct = settings.deposit_commission_percent
    pay_amount = (credit * (Decimal(1) + pct / Decimal(100))).quantize(
        _CENTS, rounding=ROUND_HALF_UP
    )
    commission = pay_amount - credit

    try:
        invoice = await crypto_pay.create_invoice(
            amount=pay_amount,
            description=f"Пополнение баланса на {credit} USDT",
            payload=json.dumps({"tg_id": message.from_user.id, "credit": str(credit)}),
            expires_in=_INVOICE_TTL,
        )
    except crypto_pay.CryptoPayError as exc:
        logger.warning("createInvoice failed: %s", exc)
        await _show(texts.DEPOSIT_INVOICE_ERROR, keyboards.deposit_back())
        return

    await state.set_state(WalletStates.awaiting_deposit_payment)
    await state.update_data(invoice_id=invoice.invoice_id)
    await _show(
        texts.deposit_invoice(pay_amount, credit),
        keyboards.deposit_invoice(invoice.pay_url),
    )

    _cancel_watcher(message.from_user.id)
    _watchers[message.from_user.id] = asyncio.create_task(
        _watch_invoice(
            bot,
            chat_id,
            message_id,
            message.from_user.id,
            invoice.invoice_id,
            credit,
            commission,
            pct,
        )
    )


@router.message(SearchStates.awaiting_query)
async def on_search_query(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    """Look up a user by the typed @username / id / t.me link and render the same
    card as the profile (or a 'not found' notice). The result replaces the prompt
    message so the section stays a single screen."""
    query = _parse_search_query(message.text or "")
    with suppress(TelegramBadRequest):
        await message.delete()

    data = await state.get_data()
    chat_id = data.get("prompt_chat_id", message.chat.id)
    message_id = data.get("prompt_message_id")
    if message_id is None:
        return

    async def _show(text: str, markup) -> None:
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id, reply_markup=markup
            )

    service = UserService(session)
    user = None
    if query:
        if query.isdigit():
            user = await service.get_by_app_id(query)
        else:
            user = await service.get_by_username(query)

    if user is None:
        await _show(texts.SEARCH_NOT_FOUND, keyboards.back_to_menu())
        return

    text = texts.profile(
        username=user.username,
        app_id=user.app_id,
        deposit=user.deposit,
        deposit_rub=await _deposit_in_rub(user.deposit),
        registered_at=user.registered_at,
    )
    await _show(text, keyboards.back_to_menu())


async def _find_unclaimed_check(
    session: AsyncSession, user_id: int
) -> crypto_pay.Check | None:
    """Return the user's still-unclaimed withdrawal check, if any. Re-checks every
    locally-'active' withdrawal against CryptoBot, flips settled ones to their live
    status (so they stop blocking) and marks deleted ones 'gone', then returns the
    first check still 'active'. On an API error returns None — best-effort, never
    locks the user out."""
    service = TransactionService(session)
    pending = await service.list_active_withdrawals(user_id)
    by_id = {int(t.external_id): t for t in pending if t.external_id}
    if not by_id:
        return None
    try:
        checks = await crypto_pay.get_checks(list(by_id))
    except crypto_pay.CryptoPayError as exc:
        logger.warning("Withdraw guard getChecks failed: %s", exc)
        return None

    unclaimed: crypto_pay.Check | None = None
    seen: set[int] = set()
    changed = False
    for chk in checks:
        seen.add(chk.check_id)
        txn = by_id.get(chk.check_id)
        if txn is None:
            continue
        if chk.status == "active":
            if unclaimed is None:
                unclaimed = chk
        else:
            txn.status = chk.status or "activated"
            changed = True
    for cid, txn in by_id.items():
        if cid not in seen:
            txn.status = "gone"
            changed = True
    if changed:
        await session.commit()
    return unclaimed


@router.callback_query(F.data == "wallet:withdraw")
async def cb_wallet_withdraw(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    _cancel_watcher(callback.from_user.id)
    await _show_withdraw_prompt(callback, state, session)


@router.message(WalletStates.awaiting_withdraw_amount)
async def on_withdraw_amount(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    """Validate the typed amount against the balance, create a Crypto Pay check for
    it, debit the balance and deliver the check as forwardable messages."""
    amount = _parse_amount(message.text or "")
    with suppress(TelegramBadRequest):
        await message.delete()

    data = await state.get_data()
    chat_id = data.get("prompt_chat_id", message.chat.id)
    message_id = data.get("prompt_message_id")
    if message_id is None:
        return

    async def _show(text: str, markup) -> None:
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id, reply_markup=markup
            )

    user = await UserService(session).get_by_telegram_id(message.from_user.id)
    available = user.deposit if user is not None else Decimal("0")

    if amount is None or amount <= 0:
        await _show(texts.WITHDRAW_INVALID, keyboards.withdraw_back())
        return
    amount = amount.quantize(_CENTS, rounding=ROUND_HALF_UP)
    if amount < _WITHDRAW_MIN:
        await _show(texts.WITHDRAW_BELOW_MIN, keyboards.withdraw_back())
        return
    if amount > available:
        await _show(texts.withdraw_insufficient(available), keyboards.withdraw_back())
        return

    pending_check = await _find_unclaimed_check(session, user.id)
    if pending_check is not None:
        await _show(
            texts.WITHDRAW_PENDING_CHECK,
            keyboards.withdraw_pending_check(pending_check.activate_url),
        )
        return

    pct = settings.withdraw_commission_percent
    payout = (amount * (Decimal(1) - pct / Decimal(100))).quantize(
        _CENTS, rounding=ROUND_HALF_UP
    )

    try:
        check = await crypto_pay.create_check(amount=payout)
    except crypto_pay.CryptoPayError as exc:
        logger.warning("createCheck failed: %s", exc)
        await _show(texts.WITHDRAW_CHECK_ERROR, keyboards.withdraw_back())
        return

    user.deposit = user.deposit - amount
    TransactionService(session).add_withdraw(
        user_id=user.id,
        check_id=check.check_id,
        link=check.activate_url,
        amount=amount,
        commission_percent=pct,
        commission_amount=amount - payout,
    )
    await session.commit()
    new_balance = user.deposit

    await state.clear()
    await _show(
        texts.wallet(
            deposit=new_balance,
            deposit_rub=await _deposit_in_rub(new_balance),
            deposit_commission_percent=settings.deposit_commission_percent,
            withdraw_commission_percent=settings.withdraw_commission_percent,
        ),
        keyboards.wallet_menu(),
    )
    with suppress(TelegramBadRequest):
        await bot.send_message(chat_id, texts.withdraw_check_created(payout))
    with suppress(TelegramBadRequest):
        await bot.send_message(
            chat_id,
            texts.withdraw_check_card(payout),
            reply_markup=keyboards.withdraw_check(check.activate_url),
        )
