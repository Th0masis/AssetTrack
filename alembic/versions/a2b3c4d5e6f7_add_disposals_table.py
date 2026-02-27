"""add_disposals_table

Revision ID: a2b3c4d5e6f7
Revises: 0177555239a5
Create Date: 2026-02-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = '0177555239a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.has_table(conn, 'disposals'):
        return
    op.create_table(
        'disposals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column(
            'reason',
            sa.Enum(
                'liquidation', 'sale', 'donation', 'theft', 'loss', 'transfer',
                name='disposalreason',
            ),
            nullable=False,
        ),
        sa.Column('disposed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('disposed_by', sa.Integer(), nullable=True),
        sa.Column('note', sa.String(length=2000), nullable=True),
        sa.Column('document_ref', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['items.id']),
        sa.ForeignKeyConstraint(['disposed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_disposals_id'), 'disposals', ['id'], unique=False)
    op.create_index(op.f('ix_disposals_item_id'), 'disposals', ['item_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_disposals_item_id'), table_name='disposals')
    op.drop_index(op.f('ix_disposals_id'), table_name='disposals')
    op.drop_table('disposals')
    # Drop the enum type (needed for PostgreSQL/MariaDB, no-op for SQLite)
    sa.Enum(name='disposalreason').drop(op.get_bind(), checkfirst=True)
