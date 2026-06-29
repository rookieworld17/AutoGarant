"""Service for recording wallet operations into the ``transactions`` table.

Both methods only ``add`` the row to the session — they do NOT commit, so the
caller can persist the transaction atomically together with the balance change.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction


class TransactionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, txn_id: int) -> Transaction | None:
        return await self._session.get(Transaction, txn_id)

    async def list_active_withdrawals(self, user_id: int) -> list[Transaction]:
        """Withdrawal rows whose check is still locally marked unclaimed
        (``status == "active"``) — the set the withdrawal guard re-checks."""
        result = await self._session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.kind == "withdraw",
                Transaction.status == "active",
            )
        )
        return list(result.scalars())

    def add_deposit(
        self,
        *,
        user_id: int,
        amount: Decimal,
        commission_percent: Decimal,
        commission_amount: Decimal,
    ) -> Transaction:
        """Record a settled (paid) deposit. ``amount`` is what was credited.

        No CryptoBot reference is kept: the invoice lives only 5 minutes and then
        self-destructs, so ``external_id`` is NULL and ``link`` is a dash."""
        txn = Transaction(
            user_id=user_id,
            kind="deposit",
            external_id=None,
            link="—",
            amount=amount,
            commission_percent=commission_percent,
            commission_amount=commission_amount,
            status="paid",
        )
        self._session.add(txn)
        return txn

    def add_withdraw(
        self,
        *,
        user_id: int,
        check_id: int,
        link: str | None,
        amount: Decimal,
        commission_percent: Decimal,
        commission_amount: Decimal,
    ) -> Transaction:
        """Record a withdrawal. ``amount`` is what was debited. ``status`` starts as
        "active" (check created, not yet claimed) and is flipped to "activated" /
        "gone" once the check's fate is observed (see the withdrawal guard)."""
        txn = Transaction(
            user_id=user_id,
            kind="withdraw",
            external_id=str(check_id),
            link=link,
            amount=amount,
            commission_percent=commission_percent,
            commission_amount=commission_amount,
            status="active",
        )
        self._session.add(txn)
        return txn
