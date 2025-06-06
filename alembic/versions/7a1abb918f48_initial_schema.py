"""initial schema

Revision ID: 7a1abb918f48
Revises: 1cb3e4a64fe7
Create Date: 2025-05-09 18:47:00.190129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a1abb918f48'
down_revision: Union[str, None] = '1cb3e4a64fe7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('invoices',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('tenant_id', sa.String(), nullable=False),
    sa.Column('payment_hash', sa.String(), nullable=False),
    sa.Column('amount_msat', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('customer_name', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('payment_hash')
    )
    op.create_table('receipts',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('invoice_id', sa.String(), nullable=False),
    sa.Column('pdf_url', sa.String(), nullable=True),
    sa.Column('signature', sa.String(), nullable=True),
    sa.Column('generated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('receipts')
    op.drop_table('invoices')
    # ### end Alembic commands ###
