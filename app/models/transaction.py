"""Transaction model — one row per completed wallet operation.

A single table records BOTH deposits and withdrawals (``kind``). Only operations
that actually moved money are stored: a deposit row is written only once its
invoice is **paid**, a withdrawal row once the check is created and the balance
debited. Withdrawals keep a CryptoBot reference (``external_id`` = check_id, used
by the withdrawal guard); deposits don't — their invoice self-destructs after
5 minutes, so ``external_id`` is NULL and ``link`` is a dash.

Amount conventions (``commission_amount`` is always the admin's cut):
- deposit:  ``amount`` = credited to balance; user paid ``amount + commission_amount``.
- withdraw: ``amount`` = debited from balance; user received ``amount - commission_amount``.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IntPrimaryKeyMixin
from app.models.user import User


class Transaction(IntPrimaryKeyMixin, Base):
    __tablename__ = "transactions"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True, nullable=False
    )

    kind: Mapped[str] = mapped_column(String(16), nullable=False)

    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    link: Mapped[str | None] = mapped_column(String(512), nullable=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    commission_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0"), server_default="0", nullable=False
    )
    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), server_default="0", nullable=False
    )
    commission_paid: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    status: Mapped[str] = mapped_column(String(16), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} {self.kind} user={self.user_id} "
            f"amount={self.amount} status={self.status}>"
        )
