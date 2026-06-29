"""create deals

Revision ID: c3e4f6a8d0e2
Revises: b2d3f5a7c9e1
Create Date: 2026-06-23 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3e4f6a8d0e2'
down_revision: Union[str, None] = 'b2d3f5a7c9e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'deals',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('number', sa.String(length=4), nullable=False),
        sa.Column('token', sa.String(length=32), nullable=False),
        sa.Column('owner_id', sa.BigInteger(), nullable=False),
        sa.Column('partner_id', sa.BigInteger(), nullable=True),
        sa.Column('owner_role', sa.String(length=16), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('terms', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=16), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['partner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_deals_number'), 'deals', ['number'], unique=True)
    op.create_index(op.f('ix_deals_token'), 'deals', ['token'], unique=True)
    op.create_index(op.f('ix_deals_owner_id'), 'deals', ['owner_id'], unique=False)
    op.create_index(op.f('ix_deals_partner_id'), 'deals', ['partner_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_deals_partner_id'), table_name='deals')
    op.drop_index(op.f('ix_deals_owner_id'), table_name='deals')
    op.drop_index(op.f('ix_deals_token'), table_name='deals')
    op.drop_index(op.f('ix_deals_number'), table_name='deals')
    op.drop_table('deals')
