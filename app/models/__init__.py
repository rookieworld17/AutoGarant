"""ORM models package.

Importing every model here ensures Alembic's autogenerate sees all tables
through ``Base.metadata``.
"""
from app.models.base import Base
from app.models.deal import Deal
from app.models.payout import Payout
from app.models.setting import Setting
from app.models.transaction import Transaction
from app.models.user import User

__all__ = ["Base", "User", "Setting", "Deal", "Transaction", "Payout"]
