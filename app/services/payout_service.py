"""Service for paying out accumulated commissions to the admin.

A payout sweeps every transaction with ``commission_paid is False`` (up to a
captured ``max_id`` so rows arriving mid-payout aren't silently swallowed),
flips them to paid and records one ``Payout`` row — but only after the funds
have actually been transferred (the controller calls ``settle`` post-transfer).
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payout, Transaction


class PayoutService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def pending(self) -> tuple[int, Decimal, int | None]:
        """Return (count, total commission, max transaction id) over the
        not-yet-paid-out transactions. ``max_id`` is None when there are none."""
        result = await self._session.execute(
            select(
                func.count(Transaction.id),
                func.coalesce(func.sum(Transaction.commission_amount), 0),
                func.max(Transaction.id),
            ).where(Transaction.commission_paid.is_(False))
        )
        count, total, max_id = result.one()
        return int(count), Decimal(str(total)), max_id

    async def last_payout(self) -> Payout | None:
        result = await self._session.execute(
            select(Payout).order_by(Payout.id.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def settle(self, *, max_id: int, amount: Decimal) -> Payout:
        """Mark the swept transactions (commission_paid=False, id ≤ max_id) as paid
        and record the payout. Call only AFTER the transfer to the admin succeeded."""
        await self._session.execute(
            update(Transaction)
            .where(
                Transaction.commission_paid.is_(False),
                Transaction.id <= max_id,
            )
            .values(commission_paid=True)
        )
        payout = Payout(amount=amount)
        self._session.add(payout)
        await self._session.commit()
        await self._session.refresh(payout)
        return payout
