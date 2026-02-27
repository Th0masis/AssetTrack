"""add responsible_person to items

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-02-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'c4d5e6f7a8b9'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('items') as batch_op:
        batch_op.add_column(sa.Column('responsible_person', sa.String(255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('items') as batch_op:
        batch_op.drop_column('responsible_person')
