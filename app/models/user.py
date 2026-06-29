"""User model — one row per Telegram user that interacts with the bot."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    tg_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    app_id: Mapped[str] = mapped_column(
        String(7), unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deposit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), server_default="0", nullable=False
    )

    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} app={self.app_id} tg={self.tg_id} @{self.username}>"
