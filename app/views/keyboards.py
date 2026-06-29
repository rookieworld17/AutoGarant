from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🤝 АвтоГарант", callback_data="menu:autogarant")
    builder.button(text="🔍 Поиск", callback_data="menu:search")
    builder.button(text="👤 Профиль", callback_data="menu:profile")
    builder.adjust(2, 1)
    return builder.as_markup()


def autogarant_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💸 Кошелёк", callback_data="menu:wallet")
    builder.button(text="🤝 Создать сделку", callback_data="autogarant:create")
    builder.button(text="⬅️ Назад", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def create_deal_role() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Покупатель", callback_data="deal:role:buyer")
    builder.button(text="💼 Продавец", callback_data="deal:role:seller")
    builder.button(text="⬅️ Назад", callback_data="menu:autogarant")
    builder.adjust(1)
    return builder.as_markup()


def deal_amount_back() -> InlineKeyboardMarkup:
    """A single 'back' button returning from the amount prompt to role selection."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="autogarant:create")
    return builder.as_markup()


def deal_terms_back() -> InlineKeyboardMarkup:
    """A single 'back' button returning from the terms prompt to the amount prompt."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="deal:role:buyer")
    return builder.as_markup()


def deal_confirm() -> InlineKeyboardMarkup:
    """Confirmation screen: cancel (left) and confirm (right), side by side."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="autogarant:create")
    builder.button(text="✅ Подтвердить", callback_data="deal:confirm")
    builder.adjust(2)
    return builder.as_markup()


def deal_invite_link(link: str) -> InlineKeyboardMarkup:
    """Invite message keyboard: a single button carrying the deep link."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔗 Ссылка для партнёра", url=link)
    return builder.as_markup()


def deal_created() -> InlineKeyboardMarkup:
    """Shown on the 'deal created' confirmation — back to the AutoGarant menu."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="menu:autogarant")
    return builder.as_markup()


def deal_offer(deal_id: int) -> InlineKeyboardMarkup:
    """Offer shown to the invited partner: accept (top) or reject (below)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять сделку", callback_data=f"deal:accept:{deal_id}")
    builder.button(text="❌ Отклонить", callback_data=f"deal:reject:{deal_id}")
    builder.adjust(1)
    return builder.as_markup()


def deal_payment(deal_id: int) -> InlineKeyboardMarkup:
    """Buyer's payment prompt: pay from balance or cancel the deal. The top-up
    button is reached from the 'insufficient funds' screen instead, since the
    balance is only checked once the buyer actually presses 'pay'."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏦 Оплатить", callback_data=f"deal:pay:{deal_id}")
    builder.button(text="❌ Отменить сделку", callback_data=f"deal:cancel:{deal_id}")
    builder.adjust(1)
    return builder.as_markup()


def deal_pay_confirm(deal_id: int) -> InlineKeyboardMarkup:
    """Buyer's confirm-payment screen: cancel (left) and confirm (right). Logic
    built next."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить", callback_data=f"deal:paycancel:{deal_id}")
    builder.button(text="✅ Подтвердить", callback_data=f"deal:payconfirm:{deal_id}")
    builder.adjust(2)
    return builder.as_markup()


def deal_escrow(deal_id: int) -> InlineKeyboardMarkup:
    """Buyer's screen once funds are in escrow: open a dispute or confirm receipt
    (both placeholders for now), or cancel the deal via the consent flow."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚠️ Открыть спор", callback_data=f"deal:dispute:{deal_id}")
    builder.button(text="✅ Подтвердить получение", callback_data=f"deal:receipt:{deal_id}")
    builder.button(text="❌ Отменить сделку", callback_data=f"deal:cancel:{deal_id}")
    builder.adjust(1)
    return builder.as_markup()


def deal_dispute_confirm(deal_id: int) -> InlineKeyboardMarkup:
    """Buyer's open-dispute confirmation: back to the paid deal (left) and confirm
    (right). The dispute flow itself is built in a later session."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data=f"deal:back:{deal_id}")
    builder.button(text="✅ Да, открыть спор", callback_data=f"deal:disputeconfirm:{deal_id}")
    builder.adjust(2)
    return builder.as_markup()


def dispute_admin_close(deal_id: int) -> InlineKeyboardMarkup:
    """Admin's dispute notice keyboard: a single '🔒 Закрыть спор' button."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔒 Закрыть спор", callback_data=f"dispute:close:{deal_id}")
    return builder.as_markup()


def dispute_admin_resolve(deal_id: int) -> InlineKeyboardMarkup:
    """Admin's 'which side?' keyboard: close the dispute toward the buyer (refund)
    or the seller (release the held funds). '⬅️ Назад' returns to the dispute card
    so the admin can re-read the deal before deciding."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Покупатель", callback_data=f"dispute:resolve:buyer:{deal_id}")
    builder.button(text="💼 Продавец", callback_data=f"dispute:resolve:seller:{deal_id}")
    builder.button(text="⬅️ Назад", callback_data=f"dispute:back:{deal_id}")
    builder.adjust(2, 1)
    return builder.as_markup()


def deal_receipt_confirm(deal_id: int) -> InlineKeyboardMarkup:
    """Buyer's confirm-receipt screen: back to the paid deal (left) and confirm
    (right). The confirm logic — releasing funds to the seller — is built next."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data=f"deal:back:{deal_id}")
    builder.button(text="✅ Подтвердить", callback_data=f"deal:receiptconfirm:{deal_id}")
    builder.adjust(2)
    return builder.as_markup()


def deal_completed() -> InlineKeyboardMarkup:
    """Sent to the seller on completion — a shortcut to their wallet."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💸 Кошелёк", callback_data="menu:wallet")
    return builder.as_markup()


def deal_insufficient(deal_id: int) -> InlineKeyboardMarkup:
    """Shown when the buyer's balance can't cover the deal: top up (jumps to the
    wallet) or go back to the very same deal's payment prompt."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💸 Пополнить баланс", callback_data="menu:wallet")
    builder.button(text="⬅️ Назад", callback_data=f"deal:back:{deal_id}")
    builder.adjust(1)
    return builder.as_markup()


def deal_cancel_confirm(deal_id: int) -> InlineKeyboardMarkup:
    """Owner's cancel-request confirmation: 'No' (back to the deal) on the left,
    'Yes, request cancellation' on the right."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Нет", callback_data=f"deal:back:{deal_id}")
    builder.button(text="✅ Да, запросить отмену", callback_data=f"deal:cancelreq:{deal_id}")
    builder.adjust(2)
    return builder.as_markup()


def deal_cancel_withdraw(deal_id: int) -> InlineKeyboardMarkup:
    """Owner's screen while a cancel request is pending: withdraw it. Logic later."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Отозвать запрос", callback_data=f"deal:cancelwithdraw:{deal_id}")
    return builder.as_markup()


def deal_cancel_decision(deal_id: int) -> InlineKeyboardMarkup:
    """Partner's choice on a cancel request: agree (left) or decline (right).
    Logic later."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Согласиться", callback_data=f"deal:cancelagree:{deal_id}")
    builder.button(text="❌ Отклонить", callback_data=f"deal:canceldecline:{deal_id}")
    builder.adjust(2)
    return builder.as_markup()


def deal_cancel_agree_confirm(deal_id: int) -> InlineKeyboardMarkup:
    """Partner's confirm-agree screen: 'No' (declines) left, 'Yes, cancel' right."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Нет", callback_data=f"deal:canceldecline:{deal_id}")
    builder.button(text="✅ Да, отменить", callback_data=f"deal:cancelconfirm:{deal_id}")
    builder.adjust(2)
    return builder.as_markup()


def deal_return(deal_id: int) -> InlineKeyboardMarkup:
    """A single 'back to the deal' button — re-opens the full payment screen."""
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Вернуться к сделке", callback_data=f"deal:back:{deal_id}")
    return builder.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="menu:main")
    return builder.as_markup()


def profile_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Мои сделки", callback_data="mydeals:page:1")
    builder.button(text="💸 Кошелёк", callback_data="menu:wallet")
    builder.button(text="⬅️ Назад", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def my_deals(
    *, deals: list[tuple[int, str]], page: int, total_pages: int
) -> InlineKeyboardMarkup:
    """A 'Мои сделки' page: one button per deal (carrying the page so the detail's
    'back' returns here), a Назад/Вперёд navigation row, then 'Назад в Профиль'."""
    builder = InlineKeyboardBuilder()
    for deal_id, label in deals:
        builder.button(text=label, callback_data=f"mydeals:open:{deal_id}:{page}")
    sizes = [1] * len(deals)

    nav = 0
    if page > 1:
        builder.button(text="⬅️ Назад", callback_data=f"mydeals:page:{page - 1}")
        nav += 1
    if page < total_pages:
        builder.button(text="➡️ Вперед", callback_data=f"mydeals:page:{page + 1}")
        nav += 1
    if nav:
        sizes.append(nav)

    builder.button(text="↩️ Назад в Профиль", callback_data="menu:profile")
    sizes.append(1)
    builder.adjust(*sizes)
    return builder.as_markup()


def my_deals_empty() -> InlineKeyboardMarkup:
    """Empty 'Мои сделки' list — only the way back to the profile."""
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Назад в Профиль", callback_data="menu:profile")
    return builder.as_markup()


def my_deal_back(page: int) -> InlineKeyboardMarkup:
    """Detail card opened from 'Мои сделки' — a single button back to the list page."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data=f"mydeals:page:{page}")
    return builder.as_markup()


def my_deal_actions(
    *, deal_id: int, status: str, is_buyer: bool, page: int, link: str | None = None
) -> InlineKeyboardMarkup:
    """Action buttons under the unified deal card in 'Мои сделки', by status and the
    viewer's role. Terminal/dispute statuses get only 'Назад'. The buyer (owner) is the
    cancel initiator; the seller (partner) is the consenter. Disputes can be opened by
    either side, but only from here. Always ends with a 'Назад' back to the list page."""
    builder = InlineKeyboardBuilder()
    sizes: list[int] = []

    if status == "active":
        if link is not None:
            builder.button(text="🔗 Ссылка для партнёра", url=link)
            sizes.append(1)
        builder.button(text="❌ Отменить сделку", callback_data=f"deal:cancelactive:{deal_id}")
        sizes.append(1)
    elif status == "accepted":
        if is_buyer:
            builder.button(text="🏦 Оплатить", callback_data=f"deal:pay:{deal_id}")
            builder.button(text="❌ Отменить сделку", callback_data=f"deal:cancel:{deal_id}")
            sizes.extend([1, 1])
    elif status == "escrow":
        builder.button(text="⚠️ Открыть спор", callback_data=f"deal:dispute:{deal_id}")
        sizes.append(1)
        if is_buyer:
            builder.button(text="✅ Подтвердить получение", callback_data=f"deal:receipt:{deal_id}")
            builder.button(text="❌ Отменить сделку", callback_data=f"deal:cancel:{deal_id}")
            sizes.extend([1, 1])
    elif status in ("cancelling", "escrow_cancel"):
        if is_buyer:
            builder.button(text="🔄 Отозвать запрос", callback_data=f"deal:cancelwithdraw:{deal_id}")
            sizes.append(1)
        else:
            builder.button(text="✅ Согласиться", callback_data=f"deal:cancelagree:{deal_id}")
            builder.button(text="❌ Отклонить", callback_data=f"deal:canceldecline:{deal_id}")
            sizes.append(2)

    builder.button(text="↩️ Назад", callback_data=f"mydeals:page:{page}")
    sizes.append(1)
    builder.adjust(*sizes)
    return builder.as_markup()


def deal_cancel_active_confirm(deal_id: int) -> InlineKeyboardMarkup:
    """Confirmation for cancelling a not-yet-accepted deal: 'No' (back to the card)
    left, 'Yes, cancel' (immediate) right."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Нет", callback_data=f"deal:back:{deal_id}")
    builder.button(text="✅ Да, отменить", callback_data=f"deal:cancelactiveok:{deal_id}")
    builder.adjust(2)
    return builder.as_markup()


def wallet_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Пополнить", callback_data="wallet:deposit")
    builder.button(text="➖ Вывести", callback_data="wallet:withdraw")
    builder.button(text="⬅️ Назад", callback_data="menu:profile")
    builder.adjust(2, 1)
    return builder.as_markup()


def deposit_back() -> InlineKeyboardMarkup:
    """A single 'back' button returning from the deposit prompt to the wallet."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="menu:wallet")
    return builder.as_markup()


def deposit_invoice(pay_url: str) -> InlineKeyboardMarkup:
    """Invoice screen: pay (opens CryptoBot) or cancel the top-up."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить", url=pay_url)
    builder.button(text="❌ Отменить", callback_data="deposit:cancel")
    builder.adjust(1)
    return builder.as_markup()


def deposit_expired() -> InlineKeyboardMarkup:
    """Expired-invoice screen: back to the deposit prompt to create a new one."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="wallet:deposit")
    return builder.as_markup()


def deposit_success() -> InlineKeyboardMarkup:
    """Success screen: return to the wallet."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ В кошелёк", callback_data="menu:wallet")
    return builder.as_markup()


def withdraw_back() -> InlineKeyboardMarkup:
    """A single 'back' button returning from the withdraw prompt to the wallet."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="menu:wallet")
    return builder.as_markup()


def withdraw_check(activate_url: str) -> InlineKeyboardMarkup:
    """The check card's button: open CryptoBot to claim the funds. The URL is
    forwardable — whoever activates it first receives the money."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Получить", url=activate_url)
    return builder.as_markup()


def withdraw_pending_check(activate_url: str) -> InlineKeyboardMarkup:
    """Shown when a new withdrawal is blocked by an unclaimed check: a button to
    claim the existing check, plus back to the wallet."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Получить", url=activate_url)
    builder.button(text="⬅️ Назад", callback_data="menu:wallet")
    builder.adjust(1)
    return builder.as_markup()


def admin_panel() -> InlineKeyboardMarkup:
    """Admin panel actions."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💸 Вывести комиссию", callback_data="admin:payout")
    builder.adjust(1)
    return builder.as_markup()


def admin_payout(can_pay: bool) -> InlineKeyboardMarkup:
    """Commission payout summary buttons: 'pay now' (only when there's something to
    pay and a recipient is configured) plus back to the panel."""
    builder = InlineKeyboardBuilder()
    if can_pay:
        builder.button(text="💸 Вывести сейчас", callback_data="admin:payout:confirm")
    builder.button(text="⬅️ Назад", callback_data="admin:panel")
    builder.adjust(1)
    return builder.as_markup()


def admin_back() -> InlineKeyboardMarkup:
    """A single 'back' button returning to the admin panel."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="admin:panel")
    return builder.as_markup()
