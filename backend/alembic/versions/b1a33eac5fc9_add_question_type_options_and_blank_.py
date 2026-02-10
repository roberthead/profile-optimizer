"""Add question_type options and blank_prompt to questions

Revision ID: b1a33eac5fc9
Revises: 85d41cf81615
Create Date: 2026-01-05 19:45:04.439334

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b1a33eac5fc9"
down_revision: Union[str, Sequence[str], None] = "85d41cf81615"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the enum type first
    questiontype_enum = postgresql.ENUM(
        "FREE_FORM",
        "MULTIPLE_CHOICE",
        "YES_NO",
        "FILL_IN_BLANK",
        name="questiontype",
        create_type=False,
    )
    questiontype_enum.create(op.get_bind(), checkfirst=True)

    # Add columns with default for existing rows
    op.add_column(
        "questions",
        sa.Column(
            "question_type",
            sa.Enum(
                "FREE_FORM",
                "MULTIPLE_CHOICE",
                "YES_NO",
                "FILL_IN_BLANK",
                name="questiontype",
            ),
            nullable=False,
            server_default="FREE_FORM",
        ),
    )
    op.add_column(
        "questions", sa.Column("options", postgresql.ARRAY(sa.Text()), nullable=True)
    )
    op.add_column("questions", sa.Column("blank_prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("questions", "blank_prompt")
    op.drop_column("questions", "options")
    op.drop_column("questions", "question_type")

    # Drop the enum type
    postgresql.ENUM(name="questiontype").drop(op.get_bind(), checkfirst=True)
