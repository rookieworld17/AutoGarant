"""
Formatting note:
    The bot is configured with ``parse_mode=MarkdownV2`` (see app/bot.py), so you
    format with MarkdownV2 syntax:
        *bold*  _italic_  __underline__  `mono`  ~strikethrough~
        [link](https://...)

    MarkdownV2 reserves these characters and they MUST be escaped with a
    backslash when used as literal text:
        _ * [ ] ( ) ~ ` > # + - = | { } . !
    For any *dynamic* value you splice into a message (usernames, amounts, …)
    pass it through ``escape`` below so user input can never break formatting.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

_MSK = ZoneInfo("Europe/Moscow")

ROLE_LABELS = {"buyer": "🛒 Покупатель", "seller": "💼 Продавец"}

_MD2_SPECIAL = r"_*[]()~`>#+-=|{}.!"
_MD2_TRANS = str.maketrans({c: f"\\{c}" for c in _MD2_SPECIAL})


def escape(text: str) -> str:
    return text.translate(_MD2_TRANS)


MAIN_MENU = (
    ">🛡 *AutoGarant \\- сервис безопасных сделок*\\.\n>\n"
    ">*Используйте гаранта для защиты средств и проводите сделки без лишних рисков*\\."
)

HELP = (
    "*AutoGarant — помощь*\n\n"
    "/start — открыть главное меню\n"
    "/help — показать это сообщение"
)

UNKNOWN = "🤔 Не понял команду\\. Нажмите /start, чтобы открыть меню\\."

AUTOGARANT_SECTION = (
    ">🛡️ *Автосделки*\n>\n"
    ">*Безопасные сделки с гарантией через эскроу\\.*\n>"
    ">*Без комиссии сервиса\\.*"
)
SEARCH_SECTION = ">🔍 *Введите @юзернейм или ID пользователя для поиска\\.*"

SEARCH_NOT_FOUND = ">⚠️ *Пользователь не найден\\.*"

CREATE_DEAL_ROLE = (
    ">🛡️ *Создание сделки*\n>\n"
    ">*Кем вы выступаете?*\n>\n"
    ">🛒 *Покупатель \\- вы платите и ждете товар или услугу*\n"
    ">💼 *Продавец \\- вы передаете товар или услугу и ждете оплату*"
)

DEAL_AMOUNT_PROMPT = (
    ">*Введите сумму сделки в USDT*\n>\n"
    ">*Минимум: 1 USDT*\n"
    ">*Пример: `50` или `12.5`*"
)

DEAL_AMOUNT_INVALID = (
    ">❌ *Некорректная сумма*\\.\n"
    ">*Введите число, например `50` или `12.5`\\.*"
)

DEAL_BELOW_MIN = ">❌ *Минимальная сумма сделки — 1 USDT*"

DEAL_TERMS_PROMPT = (
    ">📝 *Опишите условия сделки*\n>\n"
    ">*Эти условия увидит ваш партнёр\\. Пишите чётко — в случае спора арбитраж опирается только на них\\.*\n>\n"
    ">*Можно использовать шаблон:*\n"
    ">*— Что передаётся*\n"
    ">*— В какие сроки*\n"
    ">*— Что считается выполнением*\n"
    ">*— Что считается нарушением*"
)


def _quoted_terms(terms: str) -> str:
    """Render user terms as bold blockquote lines, keeping multiline input safe."""
    lines = terms.splitlines() or [terms]
    return "\n".join(f">*{escape(line)}*" if line.strip() else ">" for line in lines)


def _user_cell(username: str | None, app_id: str | None) -> str:
    """Render a participant as ``@username (ID: app_id)`` for deal messages."""
    user_line = f"@{escape(username)}" if username else "не указан"
    return f"{user_line} \\(ID: {escape(app_id or '')}\\)"


def deal_confirm(*, role_label: str, amount: Decimal, pay_amount: Decimal, terms: str) -> str:
    amt = escape(f"{amount:.2f} USDT")
    pay = escape(f"{pay_amount:.2f} USDT")
    return (
        ">✅ *Проверьте данные перед созданием*\n>\n"
        f">👤 *Ваша роль: {role_label}*\n"
        f">💲 *Сумма сделки: {amt}*\n"
        f">💲 *Сумма к оплате: {pay}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}\n>\n"
        ">*После подтверждения изменить данные нельзя\\.*"
    )


def deal_created(number: str) -> str:
    n = escape(number)
    return (
        f">✅ *Сделка \\#{n} создана*\n>\n"
        ">✉️ *Перешлите сообщение ниже партнёру — вход только по этой ссылке\\.*\n"
        ">⌛ *Партнёр должен принять в течение 15 минут, иначе сделка отменится\\.*"
    )


def deal_invite(*, number: str, partner_role: str, amount: Decimal) -> str:
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    role = ROLE_LABELS.get(partner_role, partner_role)
    return (
        f">🔗 *Приглашение в сделку \\#{n}*\n>\n"
        f">*Ваша роль: {role}*\n"
        f">*Сумма: {amt}*\n>\n"
        ">*Нажмите кнопку ниже чтобы принять участие\\.*"
    )


def deal_expired(
    *,
    number: str,
    owner_role: str,
    username: str | None,
    app_id: str,
    amount: Decimal,
    created_at: datetime,
    terms: str,
) -> str:
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    date = escape(created_at.astimezone(_MSK).strftime("%d.%m.%Y %H:%M"))
    owner_cell = _user_cell(username, app_id)
    buyer = owner_cell if owner_role == "buyer" else "не назначен"
    seller = owner_cell if owner_role == "seller" else "не назначен"
    return (
        f">⚠️ *Сделка \\#{n} истекла*\n>\n"
        f">🛒 *Покупатель: {buyer}*\n"
        f">💼 *Продавец: {seller}*\n"
        f">💲 *Сумма: {amt}*\n"
        f">📅 *Создана: {date}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}"
    )


DEAL_NOT_FOUND = ">❌ *Сделка не найдена*"
DEAL_INVITE_EXPIRED = ">⚠️ *Срок действия сделки истёк*"
DEAL_SELF_JOIN = ">❌ *Нельзя присоединиться к собственной сделке*"
DEAL_ALREADY_JOINED = ">✅ *Вы уже участвуете в этой сделке*"
DEAL_TAKEN = ">❌ *Сделка уже принята другим участником*"


def deal_offer(*, number: str, partner_role: str, amount: Decimal, terms: str) -> str:
    """Shown to the partner who activated the invite link — the deal details with
    accept/reject buttons. ``partner_role`` is the opposite of the owner's role."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    role = ROLE_LABELS.get(partner_role, partner_role)
    return (
        f">*📩 Приглашение в сделку \\#{n}*\n>\n"
        f">👤 *Ваша роль: {role}*\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}"
    )


def deal_accepted(
    *,
    number: str,
    owner_role: str,
    owner_username: str | None,
    owner_app_id: str | None,
    partner_username: str | None,
    partner_app_id: str | None,
    amount: Decimal,
    terms: str,
) -> str:
    """Shown to the partner right after they accept — both participants, amount and
    terms, then a 'waiting for payment' line. Buyer/seller follow ``owner_role``."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    owner_cell = _user_cell(owner_username, owner_app_id)
    partner_cell = _user_cell(partner_username, partner_app_id)
    buyer = owner_cell if owner_role == "buyer" else partner_cell
    seller = owner_cell if owner_role == "seller" else partner_cell
    return (
        f">✅ *Вы приняли сделку \\#{n}*\n>\n"
        f">🛒 *Покупатель: {buyer}*\n"
        f">💼 *Продавец: {seller}*\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}\n>\n"
        ">*Ожидаем оплату от покупателя\\.*"
    )


def deal_accepted_seller(
    *,
    number: str,
    owner_role: str,
    owner_username: str | None,
    owner_app_id: str | None,
    partner_username: str | None,
    partner_app_id: str | None,
    amount: Decimal,
    terms: str,
) -> str:
    """Pushed to the seller when the buyer accepts a seller-created deal — the
    seller didn't press accept, so the header reads as a notification, not 'Вы
    приняли'. The body mirrors :func:`deal_accepted` (both participants, amount,
    terms, awaiting-payment line)."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    who = f" @{escape(partner_username)}" if partner_username else ""
    owner_cell = _user_cell(owner_username, owner_app_id)
    partner_cell = _user_cell(partner_username, partner_app_id)
    buyer = owner_cell if owner_role == "buyer" else partner_cell
    seller = owner_cell if owner_role == "seller" else partner_cell
    return (
        f">✅ *Партнёр{who} принял сделку \\#{n}*\n>\n"
        f">🛒 *Покупатель: {buyer}*\n"
        f">💼 *Продавец: {seller}*\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}\n>\n"
        ">*Ожидаем оплату от покупателя\\.*"
    )


def deal_payment_request(
    *,
    number: str,
    amount: Decimal,
    terms: str,
    balance: Decimal,
) -> str:
    """Sent to the buyer once the deal is accepted — prompts them to pay. The
    recipient is always the buyer (the side that funds the escrow), regardless of
    whether they own the deal or joined it."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    bal = escape(f"{balance:.2f} USDT")
    role = ROLE_LABELS["buyer"]
    return (
        f">💳 *Оплата по сделке \\#{n}*\n>\n"
        f">👤 *Ваша роль: {role}*\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}\n>\n"
        f">💸 *Ваш баланс: {bal}*"
    )


def deal_pay_confirm(*, number: str, amount: Decimal) -> str:
    """Buyer's confirm-before-debit screen, shown when the balance covers the deal."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    return (
        f">❔ *Подтвердите оплату сделки \\#{n}*\n>\n"
        f">💸 *Будет списано: {amt}*"
    )


def _status_label(status: str) -> str:
    """Status line for deal cards: locked once the buyer's funds are in escrow,
    otherwise still awaiting payment."""
    return "🔒 В эскроу" if status in ("escrow", "escrow_cancel") else "⌛ Ожидание оплаты"


def deal_escrow(*, number: str, owner_role: str, amount: Decimal, terms: str) -> str:
    """Shown to the buyer once they confirm payment — funds are held in escrow."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    role = ROLE_LABELS.get(owner_role, owner_role)
    return (
        f">✅ *Сделка \\#{n} оплачена*\n>\n"
        f">👤 *Ваша роль: {role}*\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}\n>\n"
        ">*Средства в эскроу\\. Покупатель подтверждает получение \\- тогда деньги "
        "поступят продавцу\\.*"
    )


def deal_seller_escrow(*, number: str, amount: Decimal, terms: str) -> str:
    """Pushed to the seller once the buyer pays — funds are now held in escrow. No
    action buttons: the seller acts (incl. opening a dispute) from 'Мои сделки'."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    return (
        f">✅ *Сделка \\#{n} оплачена*\n>\n"
        ">👤 *Ваша роль: 💼 Продавец*\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}\n>\n"
        ">*Средства в эскроу\\. Покупатель подтверждает получение \\- тогда деньги "
        "поступят продавцу\\.*"
    )


def deal_dispute_confirm(number: str) -> str:
    """Buyer's confirm screen before opening a dispute on an escrowed deal."""
    n = escape(number)
    return (
        f">⚠️ *Открыть спор по сделке \\#{n}?*\n>\n"
        ">*Администрация свяжется с обеими участниками сделки и поможет разрешить "
        "ситуацию\\.*"
    )


def deal_dispute_opened(number: str) -> str:
    """Replaces the buyer's escrow card once they confirm opening a dispute."""
    n = escape(number)
    return (
        f">🔔 *Спор по сделке \\#{n} открыт*\n>\n"
        ">*Дождитесь, пока с вами свяжется администратор для разрешения спора\\.*\n"
        ">*Решение, в чью сторону закрыть сделку, принимает администратор\\.*"
    )


def deal_dispute_opened_partner(number: str) -> str:
    """Sent to the other side when a dispute is opened on their deal."""
    n = escape(number)
    return (
        f">🔔 *По сделке \\#{n} открыт спор*\n>\n"
        ">*Дождитесь, пока с вами свяжется администратор для разрешения спора\\.*\n"
        ">*Решение, в чью сторону закрыть сделку, принимает администратор\\.*"
    )


def deal_dispute_admin(
    *,
    number: str,
    owner_role: str,
    owner_username: str | None,
    owner_app_id: str | None,
    partner_username: str | None,
    partner_app_id: str | None,
    amount: Decimal,
    terms: str,
) -> str:
    """Sent to the admins when a dispute is opened — the deal card plus a
    '🔒 Закрыть спор' button. Buyer/seller lines follow ``owner_role``."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    owner_cell = _user_cell(owner_username, owner_app_id)
    partner_cell = _user_cell(partner_username, partner_app_id)
    buyer = owner_cell if owner_role == "buyer" else partner_cell
    seller = owner_cell if owner_role == "seller" else partner_cell
    return (
        f">🔔 *Открыт спор по сделке \\#{n}*\n>\n"
        f">🛒 *Покупатель: {buyer}*\n"
        f">💼 *Продавец: {seller}*\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}"
    )


def deal_dispute_resolve_prompt(number: str) -> str:
    """Admin's screen after tapping '🔒 Закрыть спор' — choose the winning side."""
    return f">⚖️ *В чью сторону закрыть спор \\#{escape(number)}?*"


def deal_dispute_resolved_admin(*, number: str, winner_role: str) -> str:
    """Replaces the admin's message once the dispute is resolved."""
    n = escape(number)
    label = ROLE_LABELS.get(winner_role, winner_role)
    return (
        f">✅ *Спор по сделке \\#{n} закрыт*\n>\n"
        f">⚖️ *Решение в пользу: {label}*"
    )


def deal_dispute_result(
    *,
    number: str,
    role: str,
    decision: str,
    amount: Decimal,
    terms: str,
    credited: Decimal | None = None,
    refunded: Decimal | None = None,
    balance: Decimal | None = None,
) -> str:
    """Dispute-outcome card sent to a participant. ``role`` is the recipient's own
    role, ``decision`` the winning role. A footer with the amount and new balance is
    appended on the winner's copy (``credited`` for the seller, ``refunded`` for the
    buyer)."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    role_label = ROLE_LABELS.get(role, role)
    decision_label = ROLE_LABELS.get(decision, decision)
    text = (
        f">⚖️ *Спор по сделке \\#{n} разрешён*\n>\n"
        f">👤 *Ваша роль: {role_label}*\n"
        f">⚖️ *Решение в пользу: {decision_label}*\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}"
    )
    if balance is not None and (credited is not None or refunded is not None):
        bal = escape(f"{balance:.2f} USDT")
        if credited is not None:
            text += f"\n>\n>💸 *Зачислено: {escape(f'{credited:.2f} USDT')}*\n>💸 *Баланс: {bal}*"
        else:
            text += f"\n>\n>💸 *Возвращено: {escape(f'{refunded:.2f} USDT')}*\n>💸 *Баланс: {bal}*"
    return text


def deal_receipt_confirm(
    *, number: str, owner_role: str, amount: Decimal, terms: str, status: str
) -> str:
    """Buyer's confirm screen before releasing escrow funds to the seller."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    role = ROLE_LABELS.get(owner_role, owner_role)
    return (
        f">❔ *Подтвердите завершение сделки \\#{n}*\n>\n"
        f">👤 *Ваша роль: {role}*\n"
        f">💲 *Сумма: {amt}*\n"
        f">⌛ *Статус: {_status_label(status)}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}\n>\n"
        f">💲 *Продавец получит: {amt}*\n>\n"
        ">*Нажимая «Подтвердить», вы подтверждаете что получили товар или услугу\\.*"
    )


def deal_insufficient(*, need: Decimal, available: Decimal) -> str:
    """Shown to the buyer when their balance can't cover the deal amount."""
    need_s = escape(f"{need:.2f} USDT")
    available_s = escape(f"{available:.2f} USDT")
    missing_s = escape(f"{need - available:.2f} USDT")
    return (
        ">⚠️ *Недостаточно средств для оплаты сделки*\n>\n"
        f">💲 *Нужно: {need_s}*\n"
        f">💸 *Доступно: {available_s}*\n"
        f">➕ *Не хватает: {missing_s}*\n>\n"
        ">*Пополните баланс и вернитесь к сделке\\.*"
    )


def deal_cancel_request(
    *, number: str, owner_role: str, amount: Decimal, terms: str, status: str
) -> str:
    """Owner's cancel confirmation — a request that needs the other side's consent."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    role = ROLE_LABELS.get(owner_role, owner_role)
    return (
        f">⚠️ *Запрос на отмену сделки \\#{n}*\n>\n"
        f">👤 *Ваша роль: {role}*\n"
        f">💲 *Сумма: {amt}*\n"
        f">⌛ *Статус: {_status_label(status)}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}\n>\n"
        ">*Запросить отмену? Она будет исполнена только при согласии другой стороны\\.*"
    )


def deal_cancel_pending(
    *, number: str, owner_role: str, amount: Decimal, terms: str, status: str
) -> str:
    """Owner's screen after they sent the cancel request — awaiting the partner."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    role = ROLE_LABELS.get(owner_role, owner_role)
    return (
        f">⚠️ *Запрос на отмену сделки \\#{n}*\n>\n"
        f">👤 *Ваша роль: {role}*\n"
        f">💲 *Сумма: {amt}*\n"
        f">⌛ *Статус: {_status_label(status)}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}"
    )


def deal_cancel_requested_partner(
    *,
    number: str,
    owner_role: str,
    owner_username: str | None,
    owner_app_id: str | None,
    partner_username: str | None,
    partner_app_id: str | None,
    amount: Decimal,
    terms: str,
) -> str:
    """Sent to the partner when the owner requests cancellation — their decision is
    needed. Buyer/seller lines follow ``owner_role``."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    owner_cell = _user_cell(owner_username, owner_app_id)
    partner_cell = _user_cell(partner_username, partner_app_id)
    buyer = owner_cell if owner_role == "buyer" else partner_cell
    seller = owner_cell if owner_role == "seller" else partner_cell
    return (
        f">⚠️ *Партнёр запросил отмену сделки \\#{n}*\n>\n"
        f">🛒 *Покупатель: {buyer}*\n"
        f">💼 *Продавец: {seller}*\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}"
    )


DEAL_CANCEL_WITHDRAWN = ">🔄 *Запрос на отмену отозван\\.*"


def deal_cancel_confirm_partner(
    *, number: str, partner_role: str, amount: Decimal, terms: str, status: str
) -> str:
    """Partner's screen after tapping '✅ Согласиться' — confirm before agreeing."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    role = ROLE_LABELS.get(partner_role, partner_role)
    return (
        f">⚠️ *Подтвердите отмену сделки \\#{n}*\n>\n"
        f">👤 *Ваша роль: {role}*\n"
        f">💲 *Сумма: {amt}*\n"
        f">⌛ *Статус: {_status_label(status)}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}\n>\n"
        ">*Вы уверены, что хотите согласиться на отмену?*"
    )


def deal_cancel_declined_partner(number: str) -> str:
    """Replaces the partner's request message once they decline the cancellation."""
    return f">❌ *Вы отклонили отмену сделки \\#{escape(number)}*"


def deal_cancel_declined_owner(*, number: str, amount: Decimal, terms: str) -> str:
    """Sent to the owner when the partner declines their cancel request."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    return (
        f">❌ *Партнёр отклонил отмену сделки \\#{n}*\n>\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}"
    )


def deal_cancelled(
    *,
    number: str,
    owner_role: str,
    owner_username: str | None,
    owner_app_id: str | None,
    partner_username: str | None,
    partner_app_id: str | None,
    amount: Decimal,
    terms: str,
) -> str:
    """Shown to the partner who declined the offer. Buyer/seller follow ``owner_role``."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    owner_cell = _user_cell(owner_username, owner_app_id)
    partner_cell = _user_cell(partner_username, partner_app_id)
    buyer = owner_cell if owner_role == "buyer" else partner_cell
    seller = owner_cell if owner_role == "seller" else partner_cell
    return (
        f">❌ *Сделка \\#{n} отменена*\n>\n"
        f">🛒 *Покупатель: {buyer}*\n"
        f">💼 *Продавец: {seller}*\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}"
    )


def deal_cancelled_escrow(
    *,
    number: str,
    owner_role: str,
    owner_username: str | None,
    owner_app_id: str | None,
    partner_username: str | None,
    partner_app_id: str | None,
    amount: Decimal,
    terms: str,
    refunded: Decimal | None = None,
    balance: Decimal | None = None,
) -> str:
    """Cancelled-by-mutual-consent card for a deal that was in escrow. Buyer/seller
    follow ``owner_role``. When ``refunded``/``balance`` are given (the buyer's own
    copy), a refund footer with the returned amount and new balance is appended."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    owner_cell = _user_cell(owner_username, owner_app_id)
    partner_cell = _user_cell(partner_username, partner_app_id)
    buyer = owner_cell if owner_role == "buyer" else partner_cell
    seller = owner_cell if owner_role == "seller" else partner_cell
    text = (
        f">❌ *Сделка \\#{n} отменена по взаимному согласию*\n>\n"
        f">🛒 *Покупатель: {buyer}*\n"
        f">💼 *Продавец: {seller}*\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}"
    )
    if refunded is not None and balance is not None:
        ref = escape(f"{refunded:.2f} USDT")
        bal = escape(f"{balance:.2f} USDT")
        text += (
            "\n>\n"
            f">💸 *Возвращено покупателю: {ref}*\n"
            f">💸 *Баланс: {bal}*"
        )
    return text


def deal_completed(
    *,
    number: str,
    role: str,
    amount: Decimal,
    terms: str,
    credited: Decimal | None = None,
    balance: Decimal | None = None,
) -> str:
    """Deal-completed card. ``role`` is the recipient's own role. When
    ``credited``/``balance`` are given (the seller's copy), a footer with the
    credited amount and new balance is appended."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    role_label = ROLE_LABELS.get(role, role)
    text = (
        f">✅ *Сделка \\#{n} завершена*\n>\n"
        f">👤 *Ваша роль: {role_label}*\n"
        f">💲 *Сумма: {amt}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}"
    )
    if credited is not None and balance is not None:
        cred = escape(f"{credited:.2f} USDT")
        bal = escape(f"{balance:.2f} USDT")
        text += (
            "\n>\n"
            f">💸 *Зачислено: {cred}*\n"
            f">💸 *Баланс: {bal}*"
        )
    return text


_DEAL_BUTTON_STATUS = {
    "active": ("⌛", "⌛", "Ожидание"),
    "accepted": ("⌛", "💳", "Ожидает оплаты"),
    "cancelling": ("⌛", "💳", "Ожидает оплаты"),
    "escrow": ("❇️", "🔒", "В эскроу"),
    "escrow_cancel": ("❇️", "🔒", "В эскроу"),
    "dispute": ("⚠️", "⚠️", "Спор"),
    "completed": ("✅", "✅", "Завершено"),
    "cancelled": ("❌", "❌", "Отменено"),
    "expired": ("❌", "❌", "Истекло"),
}

_DETAIL_STATUS_LABEL = {
    "active": "⌛ Ожидание",
    "accepted": "💳 Ожидает оплаты",
    "cancelling": "💳 Ожидает оплаты",
    "escrow": "🔒 В эскроу",
    "escrow_cancel": "🔒 В эскроу",
    "dispute": "⚠️ Спор",
    "completed": "✅ Завершено",
    "cancelled": "❌ Отменено",
    "expired": "❌ Истекло",
}


def my_deals(*, page: int, total_pages: int) -> str:
    """Header of a 'Мои сделки' list page."""
    return f">📋 *Мои сделки*\n>\n>*Страница {page} / {total_pages}*"


MY_DEALS_EMPTY = ">📋 *Мои сделки*\n>\n>*У вас пока нет сделок*"


def deal_button_label(*, number: str, amount: Decimal, status: str) -> str:
    """Plain-text label for a deal button in the 'Мои сделки' list, e.g.
    '❇️ #1234 · 50.00 USDT 💰 · 🔒 В эскроу'."""
    lead, st_emoji, st_label = _DEAL_BUTTON_STATUS.get(status, ("📄", "📄", status))
    return f"{lead} #{number} · {amount:.2f} USDT 💰 · {st_emoji} {st_label}"


def deal_detail(
    *,
    number: str,
    status: str,
    viewer_role: str,
    owner_role: str,
    owner_username: str | None,
    owner_app_id: str | None,
    partner_username: str | None,
    partner_app_id: str | None,
    amount: Decimal,
    terms: str,
) -> str:
    """Read-only deal card opened from 'Мои сделки'. ``viewer_role`` is the role of
    whoever opened it (owner or partner); buyer/seller lines follow ``owner_role``."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    role = ROLE_LABELS.get(viewer_role, viewer_role)
    status_label = _DETAIL_STATUS_LABEL.get(status, escape(status))
    lead = _DEAL_BUTTON_STATUS.get(status, ("📄",))[0]
    owner_cell = _user_cell(owner_username, owner_app_id)
    partner_cell = (
        _user_cell(partner_username, partner_app_id)
        if partner_username is not None or partner_app_id is not None
        else "не назначен"
    )
    buyer = owner_cell if owner_role == "buyer" else partner_cell
    seller = owner_cell if owner_role == "seller" else partner_cell
    return (
        f">{lead} *Сделка \\#{n}*\n>\n"
        f">👤 *Ваша роль: {role}*\n"
        f">🛒 *Покупатель: {buyer}*\n"
        f">💼 *Продавец: {seller}*\n"
        f">💲 *Сумма: {amt}*\n"
        f">📌 *Статус: {status_label}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}"
    )


def deal_card(
    *, number: str, viewer_role: str, amount: Decimal, status: str, terms: str
) -> str:
    """Unified deal card shown in 'Мои сделки' for every status. Identical layout
    across statuses/roles — only the buttons under it differ (see
    ``keyboards.my_deal_actions``). ``viewer_role`` is the role of whoever opened it."""
    n = escape(number)
    amt = escape(f"{amount:.2f} USDT")
    role = ROLE_LABELS.get(viewer_role, viewer_role)
    status_label = _DETAIL_STATUS_LABEL.get(status, escape(status))
    return (
        f">🛡️ *Сделка \\#{n}*\n>\n"
        f">👤 *Ваша роль: {role}*\n"
        f">💲 *Сумма: {amt}*\n"
        f">⌛ *Статус: {status_label}*\n>\n"
        ">📝 *Условия:*\n"
        f"{_quoted_terms(terms)}"
    )


def deal_cancel_active_confirm(number: str) -> str:
    """Owner's confirmation before cancelling a not-yet-accepted ('active') deal —
    no partner has joined, so it's cancelled immediately (no consent, no refund)."""
    n = escape(number)
    return (
        f">⚠️ *Отменить сделку \\#{n}?*\n>\n"
        ">*Сделка ещё не принята партнёром\\. Отмена удалит приглашение\\.*"
    )


def deal_rejected_by_partner(number: str) -> str:
    """Sent to the owner when the partner declines the offer."""
    return f">❌ *Партнёр отклонил сделку \\#{escape(number)}\\.*"


def deal_cancelled_by_owner(number: str) -> str:
    """Sent to the partner when the owner cancels the deal at the payment stage."""
    return f">❌ *Владелец отменил сделку \\#{escape(number)}\\.*"


def deal_joined(number: str) -> str:
    n = escape(number)
    return (
        f">✅ *Вы присоединились к сделке \\#{n}*\n>\n"
        ">*Детали сделки скоро будут доступны*"
    )

_RU_MONTHS_GENITIVE = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

def _format_ru_date(dt: datetime) -> str:
    return f"{dt.day} {_RU_MONTHS_GENITIVE[dt.month]} {dt.year} года"


def _format_percent(value: Decimal) -> str:
    text = f"{value:f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _money_line(deposit: Decimal, deposit_rub: Decimal | None) -> str:
    amount = escape(f"{deposit:.2f} USDT")
    rub = escape(f"≈ {deposit_rub:.0f} ₽") if deposit_rub is not None else "курс недоступен"
    return f"${amount} \\[ {rub} \\]"


def profile(
    *,
    username: str | None,
    app_id: str | None,
    deposit: Decimal,
    deposit_rub: Decimal | None,
    registered_at: datetime,
) -> str:
    username_line = f"@{escape(username)}" if username else "_не указан_"
    date_line = escape(_format_ru_date(registered_at))
    return (
        f"👤 *{username_line}* \\[ ID: `{app_id}` \\]\n\n"
        f">💰 *Депозит:* {_money_line(deposit, deposit_rub)}\n\n"
        f">📅 *В сервисе с {date_line}*"
    )


def wallet(
    *,
    deposit: Decimal,
    deposit_rub: Decimal | None,
    deposit_commission_percent: Decimal,
    withdraw_commission_percent: Decimal,
) -> str:
    commission = escape(_format_percent(deposit_commission_percent))
    withdraw_commission = escape(_format_percent(withdraw_commission_percent))
    return (
        ">💸 *Кошелёк*\n>\n"
        f">💰 *Баланс:* {_money_line(deposit, deposit_rub)}\n>\n"
        f">➕ *Пополнение — от 1 USDT · комиссия {commission}%*\n"
        f">➖ *Вывод — от 1 USDT · комиссия {withdraw_commission}%*"
    )


def deposit_prompt(deposit_commission_percent: Decimal) -> str:
    commission = escape(_format_percent(deposit_commission_percent))
    return (
        ">*Введите сумму пополнения в USDT*\n>\n"
        ">*Минимум: 1 USDT*\n"
        f">*Комиссия: {commission}% \\- списывается при зачислении*\n>\n"
        ">*Пример: `50` или `12.5`*"
    )

DEPOSIT_INVALID = (
    ">❌ *Некорректная сумма*\\.\n"
    ">*Введите число, например `50` или `12.5`\\.*"
)

DEPOSIT_BELOW_MIN = ">❌ *Минимальная сумма пополнения — 1 USDT*"

DEPOSIT_INVOICE_ERROR = (
    ">❌ *Не удалось создать счёт*\n>\n"
    ">*Попробуйте ещё раз позже*"
)

DEPOSIT_INVOICE_EXPIRED = (
    ">*Время оплаты истекло\\. Счет анулирован\\.*\n>\n"
    ">*Создайте новый счет через кошелек*"
)

def deposit_invoice(pay_amount: Decimal, credit_amount: Decimal) -> str:
    pay = escape(f"{pay_amount:.2f} USDT")
    credit = escape(f"{credit_amount:.2f} USDT")
    return (
        ">💳 *Счет создан*\n>\n"
        f">💲 *К оплате: {pay}*\n"
        f">💸 *Будет зачислено: {credit}*\n"
        ">⌛ *Счет действует 5 минут*\n>\n"
        ">*Нажмите кнопку ниже и оплатите через CryptoBot*"
    )

def deposit_success(credit_amount: Decimal, balance: Decimal) -> str:
    credit = escape(f"{credit_amount:.2f} USDT")
    bal = escape(f"{balance:.2f} USDT")
    return (
        ">✅ *Пополнение зачислено*\n>\n"
        f">*Зачислено: {credit}*\n"
        f">*Баланс: {bal}*"
    )


def withdraw_prompt(available: Decimal, withdraw_commission_percent: Decimal) -> str:
    avail = escape(f"{available:.2f} USDT")
    commission = escape(_format_percent(withdraw_commission_percent))
    return (
        ">➖ *Введите сумму вывода в USDT*\n>\n"
        f">*Минимум: 1 USDT · комиссия: {commission}%*\n"
        f">*Доступно: {avail}*"
    )

WITHDRAW_INVALID = (
    ">❌ *Некорректная сумма*\\.\n"
    ">*Введите число, например `50` или `12.5`\\.*"
)

WITHDRAW_BELOW_MIN = ">❌ *Минимальная сумма вывода — 1 USDT*"

def withdraw_insufficient(available: Decimal) -> str:
    avail = escape(f"{available:.2f} USDT")
    return (
        ">❌ *На балансе недостаточно средств*\n>\n"
        f">*Доступно: {avail}*"
    )

WITHDRAW_CHECK_ERROR = (
    ">❌ *Не удалось создать чек*\n>\n"
    ">*Попробуйте ещё раз позже*"
)

WITHDRAW_PENDING_CHECK = (
    ">❌ *У вас уже есть активный чек на вывод*\n>\n"
    ">*Сначала активируйте его \\(получите средства по кнопке ниже\\), "
    "затем сможете создать новый вывод\\.*"
)

def withdraw_check_created(amount: Decimal) -> str:
    amt = escape(f"{amount:.2f} USDT")
    return (
        f">🎁 Чек создан \\- {amt}\n>\n"
        ">*Нажмите кнопку ниже чтобы получить средства\\. "
        "Ссылку можно передать другому человеку — первый активировавший получит деньги\\.*"
    )

def withdraw_check_card(amount: Decimal) -> str:
    amt = escape(f"{amount:.2f} USDT")
    return f">💸 *{amt}*"


ADMIN_PANEL = (
    ">🛠 *Админ\\-панель*\n>\n"
    ">*Выберите действие\\.*"
)


def admin_payout_summary(
    *,
    pending_count: int,
    pending_sum: Decimal,
    last_amount: Decimal | None,
    last_at: datetime | None,
    min_payout: Decimal,
) -> str:
    psum = escape(f"{pending_sum:.2f} USDT")
    if last_at is not None and last_amount is not None:
        ldate = escape(last_at.astimezone(_MSK).strftime("%d.%m.%Y %H:%M"))
        lamt = escape(f"{last_amount:.2f} USDT")
        last_block = f">*Последняя выплата:*\n>*{ldate} \\- {lamt}*"
    else:
        last_block = ">*Последняя выплата:* _ещё не было_"
    if pending_sum <= 0:
        footer = "\n>\n>*Сейчас выводить нечего\\.*"
    elif pending_sum < min_payout:
        mn = escape(f"{min_payout:.2f} USDT")
        footer = f"\n>\n>*Минимальная сумма для вывода — {mn}\\.*"
    else:
        footer = ""
    return (
        ">💸 *Вывод комиссионных средств*\n>\n"
        f">*Невыплаченных операций:* {pending_count}\n"
        f">*К выплате:* {psum}\n>\n"
        f"{last_block}{footer}"
    )


def admin_payout_done(amount: Decimal) -> str:
    amt = escape(f"{amount:.2f} USDT")
    return (
        f">✅ *Выплачено {amt}*\n>\n"
        ">*Средства отправлены на ваш аккаунт CryptoBot\\.*"
    )


ADMIN_PAYOUT_ERROR = (
    ">❌ *Не удалось выполнить выплату*\n>\n"
    ">*Попробуйте ещё раз позже\\.*"
)

ADMIN_PAYOUT_NOTHING = ">ℹ️ *Сейчас выводить нечего\\.*"


def admin_payout_below_min(min_payout: Decimal) -> str:
    mn = escape(f"{min_payout:.2f} USDT")
    return (
        f">ℹ️ *Минимальная сумма для вывода — {mn}*\n>\n"
        ">*Накопите больше комиссии и попробуйте снова\\.*"
    )

ADMIN_PAYOUT_NO_RECIPIENT = (
    ">❌ *Получатель комиссии не настроен*\n>\n"
    ">*Задайте `COMMISSION_TG_ID` или `ADMIN_IDS` в `.env`\\.*"
)
