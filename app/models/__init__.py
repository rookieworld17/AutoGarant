"""ORM models package.

Importing every model here ensures Alembic's autogenerate sees all tables
through ``Base.metadata``.
"""
from app.models.base import Base
from app.models.setting import Setting
from app.models.user import User

__all__ = ["Base", "User", "Setting"]
