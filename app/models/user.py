"""User model — one row per Telegram user that interacts with the bot."""
from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IntPrimaryKeyMixin, TimestampMixin


class User(IntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    # Telegram identity
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # State flags
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<User id={self.id} tg={self.telegram_id} @{self.username}>"
