"""add deals cancel_request_msg_id

Revision ID: e5a6b7c8d9e0
Revises: d4f5a6b7c8d9
Create Date: 2026-06-24 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5a6b7c8d9e0'
down_revision: Union[str, None] = 'd4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'deals',
        sa.Column('cancel_request_msg_id', sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('deals', 'cancel_request_msg_id')
