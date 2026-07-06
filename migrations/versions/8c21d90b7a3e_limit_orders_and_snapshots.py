"""limit orders and portfolio snapshots

Revision ID: 8c21d90b7a3e
Revises: 5f558479fe41
Create Date: 2026-07-05 21:30:00.000000

Adds orders.limit_price (+ a status index for the fill worker's sweep) and
the portfolio_snapshots table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8c21d90b7a3e'
down_revision: Union[str, None] = '5f558479fe41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('limit_price', sa.Numeric(18, 4), nullable=True))
    op.create_index('ix_orders_status', 'orders', ['status'])

    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cash_balance', sa.Numeric(18, 4), nullable=False),
        sa.Column('positions_value', sa.Numeric(18, 4), nullable=False),
        sa.Column('total_value', sa.Numeric(18, 4), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_portfolio_snapshots_account_created',
        'portfolio_snapshots', ['account_id', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_portfolio_snapshots_account_created', table_name='portfolio_snapshots')
    op.drop_table('portfolio_snapshots')
    op.drop_index('ix_orders_status', table_name='orders')
    op.drop_column('orders', 'limit_price')
