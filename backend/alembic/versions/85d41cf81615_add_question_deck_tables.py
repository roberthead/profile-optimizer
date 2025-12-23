"""add_question_deck_tables

Revision ID: 85d41cf81615
Revises: 3698a4d10bc8
Create Date: 2025-12-22 19:47:52.724905

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '85d41cf81615'
down_revision: Union[str, Sequence[str], None] = '3698a4d10bc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum type for question categories
    question_category = postgresql.ENUM(
        'origin_story', 'creative_spark', 'collaboration', 'future_vision',
        'community_connection', 'hidden_depths', 'impact_legacy',
        name='questioncategory'
    )
    question_category.create(op.get_bind())

    # Create question_decks table
    op.create_table(
        'question_decks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('deck_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('member_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('generation_context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('deck_id')
    )
    op.create_index(op.f('ix_question_decks_id'), 'question_decks', ['id'], unique=False)
    op.create_index(op.f('ix_question_decks_deck_id'), 'question_decks', ['deck_id'], unique=True)
    op.create_index(op.f('ix_question_decks_member_id'), 'question_decks', ['member_id'], unique=False)

    # Create questions table
    op.create_table(
        'questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('deck_id', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('category', sa.Enum('origin_story', 'creative_spark', 'collaboration', 'future_vision', 'community_connection', 'hidden_depths', 'impact_legacy', name='questioncategory'), nullable=False),
        sa.Column('difficulty_level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('estimated_time_minutes', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('purpose', sa.Text(), nullable=False),
        sa.Column('follow_up_prompts', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('potential_insights', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('related_profile_fields', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['deck_id'], ['question_decks.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('question_id')
    )
    op.create_index(op.f('ix_questions_id'), 'questions', ['id'], unique=False)
    op.create_index(op.f('ix_questions_question_id'), 'questions', ['question_id'], unique=True)

    # Create question_responses table
    op.create_table(
        'question_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('led_to_suggestion', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('suggestion_id', sa.Integer(), nullable=True),
        sa.Column('engagement_rating', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id']),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id']),
        sa.ForeignKeyConstraint(['suggestion_id'], ['profile_suggestions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_responses_id'), 'question_responses', ['id'], unique=False)
    op.create_index(op.f('ix_question_responses_session_id'), 'question_responses', ['session_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_question_responses_session_id'), table_name='question_responses')
    op.drop_index(op.f('ix_question_responses_id'), table_name='question_responses')
    op.drop_table('question_responses')

    op.drop_index(op.f('ix_questions_question_id'), table_name='questions')
    op.drop_index(op.f('ix_questions_id'), table_name='questions')
    op.drop_table('questions')

    op.drop_index(op.f('ix_question_decks_member_id'), table_name='question_decks')
    op.drop_index(op.f('ix_question_decks_deck_id'), table_name='question_decks')
    op.drop_index(op.f('ix_question_decks_id'), table_name='question_decks')
    op.drop_table('question_decks')

    # Drop enum type
    sa.Enum(name='questioncategory').drop(op.get_bind())
