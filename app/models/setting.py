"""Setting model — example of a table holding mutable runtime information.

Use this as a template for the other "changing information" tables the
project will need (prices, statuses, dynamic content, etc.).
"""
from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IntPrimaryKeyMixin, TimestampMixin


class Setting(IntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Setting {self.key}={self.value!r}>"
