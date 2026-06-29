"""add transactions commission_paid

Revision ID: a7b8c9d0e1f2
Revises: f6b7c8d9e0f1
Create Date: 2026-06-29 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6b7c8d9e0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'transactions',
        sa.Column(
            'commission_paid',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('transactions', 'commission_paid')
