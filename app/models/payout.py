"""Payout model — one row per commission payout actually sent to the admin.

A row is written ONLY after the funds have been transferred to the admin's
CryptoBot account; ``amount`` is the total paid out and ``created_at`` is the
payout date. Each payout settles the transactions whose commission it covered
(their ``commission_paid`` flips to True — see [[commission-transfer]]).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IntPrimaryKeyMixin


class Payout(IntPrimaryKeyMixin, Base):
    __tablename__ = "payouts"

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Payout id={self.id} amount={self.amount} at={self.created_at}>"
