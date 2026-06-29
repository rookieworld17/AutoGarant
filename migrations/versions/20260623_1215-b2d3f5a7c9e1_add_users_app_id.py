"""add users.app_id

Revision ID: b2d3f5a7c9e1
Revises: a1c2e3f4d5b6
Create Date: 2026-06-23 12:15:00.000000
"""
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2d3f5a7c9e1'
down_revision: Union[str, None] = 'a1c2e3f4d5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('app_id', sa.String(length=7), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM users WHERE app_id IS NULL")).fetchall()
    used: set[str] = {
        r[0] for r in bind.execute(
            sa.text("SELECT app_id FROM users WHERE app_id IS NOT NULL")
        ).fetchall()
    }
    for (user_id,) in rows:
        while True:
            candidate = f"{secrets.randbelow(10_000_000):07d}"
            if candidate not in used:
                used.add(candidate)
                break
        bind.execute(
            sa.text("UPDATE users SET app_id = :app_id WHERE id = :id"),
            {"app_id": candidate, "id": user_id},
        )

    op.alter_column('users', 'app_id', nullable=False)
    op.create_index(op.f('ix_users_app_id'), 'users', ['app_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_app_id'), table_name='users')
    op.drop_column('users', 'app_id')
