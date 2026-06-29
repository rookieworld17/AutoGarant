"""Minimal async client for the Crypto Pay API (CryptoBot).

Docs: https://help.send.tg/en/articles/10279948-crypto-pay-api

Only the few methods the deposit/withdraw flows need are implemented: createInvoice,
getInvoices (to poll a single invoice's status), deleteInvoice, createCheck (a
claimable payout link) and transfer (send funds straight to a user's CryptoBot
account — used to auto-forward commissions to the admin). The base URL switches
between testnet and mainnet via ``settings.crypto_pay_testnet``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)

_MAINNET_URL = "https://pay.crypt.bot/api"
_TESTNET_URL = "https://testnet-pay.crypt.bot/api"
_TIMEOUT = 10.0


class CryptoPayError(RuntimeError):
    """Raised when the Crypto Pay API returns ``ok: false`` or is unreachable."""


@dataclass(slots=True)
class Invoice:
    invoice_id: int
    status: str
    amount: Decimal
    asset: str
    pay_url: str

    @property
    def is_paid(self) -> bool:
        return self.status == "paid"


@dataclass(slots=True)
class Check:
    check_id: int
    status: str
    amount: Decimal
    asset: str
    activate_url: str


def _base_url() -> str:
    return _TESTNET_URL if settings.crypto_pay_testnet else _MAINNET_URL


def _parse_invoice(data: dict) -> Invoice:
    return Invoice(
        invoice_id=int(data["invoice_id"]),
        status=str(data["status"]),
        amount=Decimal(str(data.get("amount", "0"))),
        asset=str(data.get("asset", "")),
        pay_url=str(
            data.get("bot_invoice_url")
            or data.get("mini_app_invoice_url")
            or data.get("web_app_invoice_url")
            or ""
        ),
    )


async def _call(method: str, payload: dict) -> object:
    """POST to a Crypto Pay method and return the ``result`` field."""
    url = f"{_base_url()}/{method}"
    headers = {"Crypto-Pay-API-Token": settings.crypto_pay_token}
    timeout = aiohttp.ClientTimeout(total=_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as http:
            async with http.post(url, json=payload, headers=headers) as resp:
                data = await resp.json(content_type=None)
    except aiohttp.ClientError as exc:
        raise CryptoPayError(f"network error: {exc}") from exc

    if not data.get("ok"):
        raise CryptoPayError(str(data.get("error")))
    return data["result"]


async def create_invoice(
    *,
    amount: Decimal,
    description: str | None = None,
    payload: str | None = None,
    expires_in: int = 300,
    asset: str = "USDT",
) -> Invoice:
    """Create a crypto invoice. ``amount`` is the total the user must pay."""
    body: dict[str, object] = {
        "asset": asset,
        "amount": f"{amount:.2f}",
        "expires_in": expires_in,
    }
    if description:
        body["description"] = description
    if payload:
        body["payload"] = payload
    result = await _call("createInvoice", body)
    return _parse_invoice(result)


def _parse_check(data: dict) -> Check:
    return Check(
        check_id=int(data["check_id"]),
        status=str(data.get("status", "")),
        amount=Decimal(str(data.get("amount", "0"))),
        asset=str(data.get("asset", "")),
        activate_url=str(data.get("bot_check_url") or ""),
    )


async def create_check(*, amount: Decimal, asset: str = "USDT") -> Check:
    """Create a crypto check — a claimable link funded from the app's Crypto Pay
    balance. The first person to activate the link receives ``amount``."""
    body: dict[str, object] = {
        "asset": asset,
        "amount": f"{amount:.2f}",
    }
    result = await _call("createCheck", body)
    return _parse_check(result)


@dataclass(slots=True)
class Transfer:
    transfer_id: int
    status: str
    amount: Decimal
    asset: str


def _parse_transfer(data: dict) -> Transfer:
    return Transfer(
        transfer_id=int(data["transfer_id"]),
        status=str(data.get("status", "")),
        amount=Decimal(str(data.get("amount", "0"))),
        asset=str(data.get("asset", "")),
    )


async def create_transfer(
    *,
    user_id: int,
    amount: Decimal,
    spend_id: str,
    asset: str = "USDT",
    comment: str | None = None,
) -> Transfer:
    """Transfer ``amount`` from the app's Crypto Pay balance to a Telegram user.

    ``spend_id`` is an arbitrary unique string (≤64 chars) that makes the call
    idempotent — retrying with the same id never sends twice. The recipient must
    have an active CryptoBot account, and ``amount`` must clear the asset's
    per-transfer minimum or the API rejects it.
    """
    body: dict[str, object] = {
        "user_id": user_id,
        "asset": asset,
        "amount": f"{amount:.2f}",
        "spend_id": spend_id,
    }
    if comment:
        body["comment"] = comment
    result = await _call("transfer", body)
    return _parse_transfer(result)


async def get_invoice(invoice_id: int) -> Invoice | None:
    """Fetch a single invoice by id (used to poll its status)."""
    result = await _call("getInvoices", {"invoice_ids": str(invoice_id)})
    items = result.get("items") if isinstance(result, dict) else result
    if not items:
        return None
    return _parse_invoice(items[0])


async def get_checks(check_ids: list[int]) -> list[Check]:
    """Fetch checks by id (used to inspect their activation status). A check that
    was deleted simply won't appear in the result."""
    if not check_ids:
        return []
    ids = ",".join(str(c) for c in check_ids)
    result = await _call("getChecks", {"check_ids": ids})
    items = result.get("items") if isinstance(result, dict) else result
    return [_parse_check(item) for item in (items or [])]


async def delete_invoice(invoice_id: int) -> bool:
    """Delete an invoice. Returns False instead of raising on failure."""
    try:
        await _call("deleteInvoice", {"invoice_id": invoice_id})
        return True
    except CryptoPayError as exc:
        logger.warning("deleteInvoice(%s) failed: %s", invoice_id, exc)
        return False
