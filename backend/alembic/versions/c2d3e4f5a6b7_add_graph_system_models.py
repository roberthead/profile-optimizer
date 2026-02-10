"""Add graph system models - edges, taste profiles, event signals, question deliveries

Revision ID: c2d3e4f5a6b7
Revises: b1a33eac5fc9
Create Date: 2026-02-09 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'b1a33eac5fc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add graph system models."""

    # ==========================================================================
    # Create new enum types
    # ==========================================================================

    edgetype_enum = postgresql.ENUM(
        'shared_skill', 'shared_interest', 'collaboration_potential',
        'event_co_attendance', 'introduced_by_agent', 'pattern_connection',
        name='edgetype', create_type=False
    )
    edgetype_enum.create(op.get_bind(), checkfirst=True)

    signaltype_enum = postgresql.ENUM(
        'viewed', 'clicked', 'rsvp', 'attended', 'skipped', 'shared', 'organized',
        name='signaltype', create_type=False
    )
    signaltype_enum.create(op.get_bind(), checkfirst=True)

    deliverychannel_enum = postgresql.ENUM(
        'mobile_swipe', 'clubhouse_display', 'email', 'sms', 'web_chat',
        name='deliverychannel', create_type=False
    )
    deliverychannel_enum.create(op.get_bind(), checkfirst=True)

    deliverystatus_enum = postgresql.ENUM(
        'pending', 'delivered', 'viewed', 'answered', 'skipped', 'expired',
        name='deliverystatus', create_type=False
    )
    deliverystatus_enum.create(op.get_bind(), checkfirst=True)

    questionvibe_enum = postgresql.ENUM(
        'warm', 'playful', 'deep', 'edgy', 'connector',
        name='questionvibe', create_type=False
    )
    questionvibe_enum.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # Create member_edges table
    # ==========================================================================

    op.create_table(
        'member_edges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('member_a_id', sa.Integer(), nullable=False),
        sa.Column('member_b_id', sa.Integer(), nullable=False),
        sa.Column('edge_type', sa.Enum('shared_skill', 'shared_interest', 'collaboration_potential',
                                        'event_co_attendance', 'introduced_by_agent', 'pattern_connection',
                                        name='edgetype'), nullable=False),
        sa.Column('strength', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('discovered_via', sa.String(100), nullable=False),
        sa.Column('evidence', postgresql.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['member_a_id'], ['members.id'], ),
        sa.ForeignKeyConstraint(['member_b_id'], ['members.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_member_edges_id', 'member_edges', ['id'])
    op.create_index('ix_member_edges_member_a_id', 'member_edges', ['member_a_id'])
    op.create_index('ix_member_edges_member_b_id', 'member_edges', ['member_b_id'])
    op.create_index('ix_member_edges_edge_type', 'member_edges', ['edge_type'])

    # ==========================================================================
    # Create taste_profiles table
    # ==========================================================================

    op.create_table(
        'taste_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        # Explicit preferences
        sa.Column('vibe_words', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('avoid_words', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('energy_time', sa.String(50), nullable=True),
        sa.Column('usual_company', sa.String(50), nullable=True),
        sa.Column('spontaneity', sa.Integer(), nullable=False, server_default='50'),
        # Anti-preferences
        sa.Column('dealbreakers', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('not_my_thing', postgresql.ARRAY(sa.String()), nullable=True),
        # Implicit preferences (JSON)
        sa.Column('category_affinities', postgresql.JSON(), nullable=True),
        sa.Column('venue_affinities', postgresql.JSON(), nullable=True),
        sa.Column('organizer_affinities', postgresql.JSON(), nullable=True),
        sa.Column('price_comfort', postgresql.JSON(), nullable=True),
        # Contextual state
        sa.Column('current_mood', sa.String(100), nullable=True),
        sa.Column('this_week_energy', sa.String(50), nullable=True),
        sa.Column('visitors_in_town', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('context_updated_at', sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('member_id')
    )
    op.create_index('ix_taste_profiles_id', 'taste_profiles', ['id'])
    op.create_index('ix_taste_profiles_member_id', 'taste_profiles', ['member_id'])

    # ==========================================================================
    # Create event_signals table
    # ==========================================================================

    op.create_table(
        'event_signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('rova_event_id', sa.String(100), nullable=False),
        sa.Column('rova_event_slug', sa.String(255), nullable=False),
        sa.Column('signal_type', sa.Enum('viewed', 'clicked', 'rsvp', 'attended', 'skipped', 'shared', 'organized',
                                          name='signaltype'), nullable=False),
        sa.Column('signal_strength', sa.Integer(), nullable=False),
        # Denormalized event context
        sa.Column('event_category', sa.String(100), nullable=True),
        sa.Column('event_venue_slug', sa.String(255), nullable=True),
        sa.Column('event_organizer_slug', sa.String(255), nullable=True),
        sa.Column('event_tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('event_time_of_day', sa.String(50), nullable=True),
        sa.Column('event_day_of_week', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_event_signals_id', 'event_signals', ['id'])
    op.create_index('ix_event_signals_member_id', 'event_signals', ['member_id'])
    op.create_index('ix_event_signals_rova_event_id', 'event_signals', ['rova_event_id'])
    op.create_index('ix_event_signals_signal_type', 'event_signals', ['signal_type'])

    # ==========================================================================
    # Create question_deliveries table
    # ==========================================================================

    op.create_table(
        'question_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.Enum('mobile_swipe', 'clubhouse_display', 'email', 'sms', 'web_chat',
                                      name='deliverychannel'), nullable=False),
        sa.Column('delivery_status', sa.Enum('pending', 'delivered', 'viewed', 'answered', 'skipped', 'expired',
                                              name='deliverystatus'), nullable=False, server_default='pending'),
        # Timestamps
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('answered_at', sa.DateTime(timezone=True), nullable=True),
        # Response data
        sa.Column('response_type', sa.String(50), nullable=True),
        sa.Column('response_value', sa.Text(), nullable=True),
        sa.Column('response_time_seconds', sa.Integer(), nullable=True),
        # Targeting context
        sa.Column('targeting_context', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_question_deliveries_id', 'question_deliveries', ['id'])
    op.create_index('ix_question_deliveries_question_id', 'question_deliveries', ['question_id'])
    op.create_index('ix_question_deliveries_member_id', 'question_deliveries', ['member_id'])
    op.create_index('ix_question_deliveries_channel', 'question_deliveries', ['channel'])

    # ==========================================================================
    # Extend questions table with graph context
    # ==========================================================================

    op.add_column('questions', sa.Column('relevant_member_ids', postgresql.ARRAY(sa.Integer()), nullable=True))
    op.add_column('questions', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('edge_context', postgresql.JSON(), nullable=True))
    op.add_column('questions', sa.Column('targeting_criteria', postgresql.JSON(), nullable=True))
    op.add_column('questions', sa.Column('vibe', sa.Enum('warm', 'playful', 'deep', 'edgy', 'connector',
                                                          name='questionvibe'), nullable=True))

    # ==========================================================================
    # Extend patterns table with graph metadata
    # ==========================================================================

    op.add_column('patterns', sa.Column('edge_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('patterns', sa.Column('question_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('patterns', sa.Column('last_question_generated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('patterns', sa.Column('vitality_score', sa.Integer(), nullable=False, server_default='50'))


def downgrade() -> None:
    """Downgrade schema - remove graph system models."""

    # Remove columns from patterns
    op.drop_column('patterns', 'vitality_score')
    op.drop_column('patterns', 'last_question_generated_at')
    op.drop_column('patterns', 'question_count')
    op.drop_column('patterns', 'edge_count')

    # Remove columns from questions
    op.drop_column('questions', 'vibe')
    op.drop_column('questions', 'targeting_criteria')
    op.drop_column('questions', 'edge_context')
    op.drop_column('questions', 'notes')
    op.drop_column('questions', 'relevant_member_ids')

    # Drop tables
    op.drop_table('question_deliveries')
    op.drop_table('event_signals')
    op.drop_table('taste_profiles')
    op.drop_table('member_edges')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS questionvibe')
    op.execute('DROP TYPE IF EXISTS deliverystatus')
    op.execute('DROP TYPE IF EXISTS deliverychannel')
    op.execute('DROP TYPE IF EXISTS signaltype')
    op.execute('DROP TYPE IF EXISTS edgetype')
