"""Add cafe_drops engagement rewards to members

Revision ID: d5e6f7a8b9c0
Revises: c2d3e4f5a6b7
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add cafe drops engagement fields to members
    op.add_column('members', sa.Column('cafe_drops', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('members', sa.Column('drops_earned_today', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('members', sa.Column('last_drop_earned_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('members', sa.Column('streak_days', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    op.drop_column('members', 'streak_days')
    op.drop_column('members', 'last_drop_earned_at')
    op.drop_column('members', 'drops_earned_today')
    op.drop_column('members', 'cafe_drops')
