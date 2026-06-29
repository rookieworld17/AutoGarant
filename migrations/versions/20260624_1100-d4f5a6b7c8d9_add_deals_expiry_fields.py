"""add deals expiry fields

Revision ID: d4f5a6b7c8d9
Revises: c3e4f6a8d0e2
Create Date: 2026-06-24 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4f5a6b7c8d9'
down_revision: Union[str, None] = 'c3e4f6a8d0e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('deals', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.drop_column('deals', 'updated_at')


def downgrade() -> None:
    op.add_column(
        'deals',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    op.drop_column('deals', 'expires_at')
