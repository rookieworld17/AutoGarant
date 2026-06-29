"""Deal model — one escrow deal between an owner and a partner."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IntPrimaryKeyMixin
from app.models.user import User


class Deal(IntPrimaryKeyMixin, Base):
    __tablename__ = "deals"

    number: Mapped[str] = mapped_column(String(4), unique=True, index=True, nullable=False)
    token: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)

    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True, nullable=False
    )
    partner_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True, nullable=True
    )

    owner_role: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    terms: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="active", server_default="active", nullable=False
    )

    cancel_request_msg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped[User] = relationship("User", foreign_keys=[owner_id])
    partner: Mapped[User | None] = relationship("User", foreign_keys=[partner_id])

    def __repr__(self) -> str:
        return f"<Deal #{self.number} status={self.status} owner={self.owner_id}>"
