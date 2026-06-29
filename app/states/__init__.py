"""FSM state groups live here."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class WalletStates(StatesGroup):
    """Multi-step wallet flows (deposit / withdraw)."""

    awaiting_deposit_amount = State()
    awaiting_deposit_payment = State()
    awaiting_withdraw_amount = State()


class DealStates(StatesGroup):
    """Multi-step deal creation flow."""

    awaiting_amount = State()
    awaiting_terms = State()
    awaiting_confirm = State()


class SearchStates(StatesGroup):
    """User lookup flow in the 'Поиск' section."""

    awaiting_query = State()


__all__ = ["WalletStates", "DealStates", "SearchStates"]
