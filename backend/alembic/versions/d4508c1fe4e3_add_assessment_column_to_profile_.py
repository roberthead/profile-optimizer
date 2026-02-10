"""Add assessment column to profile_completeness

Revision ID: d4508c1fe4e3
Revises: f1ca9ebf436c
Create Date: 2025-12-08 19:18:30.000619

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4508c1fe4e3"
down_revision: Union[str, Sequence[str], None] = "f1ca9ebf436c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "profile_completeness", sa.Column("assessment", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("profile_completeness", "assessment")
