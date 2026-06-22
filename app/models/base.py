"""Declarative base and shared mixins for all ORM models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for every ORM model in the project."""


class TimestampMixin:
    """Adds automatically managed created_at / updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class IntPrimaryKeyMixin:
    """Standard auto-incrementing big-integer primary key."""

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
