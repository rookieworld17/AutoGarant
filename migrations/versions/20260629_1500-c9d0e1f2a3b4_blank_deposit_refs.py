"""blank cryptobot refs on deposit transactions

Deposits no longer keep a CryptoBot reference: the invoice lives only 5 minutes
and then self-destructs, so its id / pay link are useless afterwards. Clear them
on existing deposit rows (external_id -> NULL, link -> '—') to match new writes.
Withdrawals keep their check_id, so only deposit rows are touched.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-29 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE transactions SET external_id = NULL, link = '—' "
        "WHERE kind = 'deposit'"
    )


def downgrade() -> None:
    pass
