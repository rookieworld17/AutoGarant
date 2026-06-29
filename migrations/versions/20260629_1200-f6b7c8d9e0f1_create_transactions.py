"""create transactions

Revision ID: f6b7c8d9e0f1
Revises: e5a6b7c8d9e0
Create Date: 2026-06-29 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6b7c8d9e0f1'
down_revision: Union[str, None] = 'e5a6b7c8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('external_id', sa.String(length=64), nullable=True),
        sa.Column('link', sa.String(length=512), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('commission_percent', sa.Numeric(precision=5, scale=2), server_default='0', nullable=False),
        sa.Column('commission_amount', sa.Numeric(precision=12, scale=2), server_default='0', nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_transactions_user_id'), 'transactions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transactions_user_id'), table_name='transactions')
    op.drop_table('transactions')
