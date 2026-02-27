"""add closed_by to audits

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-02-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'b3c4d5e6f7a8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('audits') as batch_op:
        batch_op.add_column(sa.Column('closed_by', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('audits') as batch_op:
        batch_op.drop_column('closed_by')
