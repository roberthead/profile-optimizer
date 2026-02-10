"""add related_pattern_ids to questions

Revision ID: a7e2f1b3c4d5
Revises: b1a33eac5fc9
Create Date: 2026-02-09 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7e2f1b3c4d5"
down_revision: Union[str, Sequence[str], None] = "b1a33eac5fc9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add related_pattern_ids column to questions table."""
    op.add_column(
        "questions",
        sa.Column("related_pattern_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
    )


def downgrade() -> None:
    """Remove related_pattern_ids column from questions table."""
    op.drop_column("questions", "related_pattern_ids")
