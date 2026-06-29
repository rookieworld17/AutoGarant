"""initial schema

Revision ID: a1c2e3f4d5b6
Revises:
Create Date: 2026-06-23 10:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c2e3f4d5b6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'settings',
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_settings_key'), 'settings', ['key'], unique=True)

    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tg_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('phone_number', sa.String(length=32), nullable=True),
        sa.Column('deposit', sa.Numeric(precision=12, scale=2), server_default='0', nullable=False),
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_tg_id'), 'users', ['tg_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_tg_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_settings_key'), table_name='settings')
    op.drop_table('settings')
