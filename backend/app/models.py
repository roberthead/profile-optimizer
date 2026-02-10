from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List
import uuid
from app.core.database import Base
from pgvector.sqlalchemy import Vector


class QuestionCategory(str, PyEnum):
    """Categories for questions to help with organization and gamification."""
    ORIGIN_STORY = "origin_story"
    CREATIVE_SPARK = "creative_spark"
    COLLABORATION = "collaboration"
    FUTURE_VISION = "future_vision"
    COMMUNITY_CONNECTION = "community_connection"
    HIDDEN_DEPTHS = "hidden_depths"
    IMPACT_LEGACY = "impact_legacy"


class QuestionType(str, PyEnum):
    """Types of questions based on answer format."""
    FREE_FORM = "free_form"           # Open-ended text response
    MULTIPLE_CHOICE = "multiple_choice"  # Select from predefined options
    YES_NO = "yes_no"                 # Simple yes/no question
    FILL_IN_BLANK = "fill_in_blank"   # Complete a sentence


class PatternCategory(str, PyEnum):
    """Categories for discovered community patterns."""
    SKILL_CLUSTER = "skill_cluster"           # Groups of related skills that appear together
    INTEREST_THEME = "interest_theme"         # Common interest areas/passions
    COLLABORATION_OPPORTUNITY = "collaboration_opportunity"  # Complementary skills/potential partnerships
    COMMUNITY_STRENGTH = "community_strength" # Core competencies of the community
    CROSS_DOMAIN = "cross_domain"             # Interesting overlaps between different areas


class EdgeType(str, PyEnum):
    """Types of connections between members."""
    SHARED_SKILL = "shared_skill"
    SHARED_INTEREST = "shared_interest"
    COLLABORATION_POTENTIAL = "collaboration_potential"
    EVENT_CO_ATTENDANCE = "event_co_attendance"
    INTRODUCED_BY_AGENT = "introduced_by_agent"
    PATTERN_CONNECTION = "pattern_connection"


class SignalType(str, PyEnum):
    """Types of event interaction signals."""
    VIEWED = "viewed"
    CLICKED = "clicked"
    RSVP = "rsvp"
    ATTENDED = "attended"
    SKIPPED = "skipped"
    SHARED = "shared"
    ORGANIZED = "organized"


class DeliveryChannel(str, PyEnum):
    """Channels for question delivery."""
    MOBILE_SWIPE = "mobile_swipe"
    CLUBHOUSE_DISPLAY = "clubhouse_display"
    EMAIL = "email"
    SMS = "sms"
    WEB_CHAT = "web_chat"


class DeliveryStatus(str, PyEnum):
    """Status of question delivery."""
    PENDING = "pending"
    DELIVERED = "delivered"
    VIEWED = "viewed"
    ANSWERED = "answered"
    SKIPPED = "skipped"
    EXPIRED = "expired"


class QuestionVibe(str, PyEnum):
    """Vibe/tone of questions for matching to member energy."""
    WARM = "warm"           # Friendly, approachable
    PLAYFUL = "playful"     # Fun, light-hearted
    DEEP = "deep"           # Thoughtful, introspective
    EDGY = "edgy"           # Provocative, challenging
    CONNECTOR = "connector" # About relationships/introductions


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4)
    clerk_user_id: Mapped[str] = mapped_column(String, unique=True, index=True)  # Link to Clerk User
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String)
    last_name: Mapped[Optional[str]] = mapped_column(String)
    profile_photo_url: Mapped[Optional[str]] = mapped_column(String)

    # Profile Content
    bio: Mapped[Optional[str]] = mapped_column(Text)
    company: Mapped[Optional[str]] = mapped_column(String)
    role: Mapped[Optional[str]] = mapped_column(String)  # e.g. "Software Engineer", "Shift Companion"
    website: Mapped[Optional[str]] = mapped_column(String)
    location: Mapped[Optional[str]] = mapped_column(String)

    # Membership
    membership_status: Mapped[str] = mapped_column(String, default="free")  # free, active_create, active_fellow, etc.
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)

    # Arrays stored as JSON (skills, interests, etc.)
    urls: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    roles: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)  # Community roles
    prompt_responses: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=list)
    skills: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    interests: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    all_traits: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)

    # Engagement rewards
    cafe_drops: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    drops_earned_today: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    last_drop_earned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    streak_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    social_links: Mapped[List["SocialLink"]] = relationship(back_populates="member", cascade="all, delete-orphan")
    conversation_history: Mapped[List["ConversationHistory"]] = relationship(back_populates="member", cascade="all, delete-orphan")
    profile_completeness: Mapped[Optional["ProfileCompleteness"]] = relationship(back_populates="member", uselist=False, cascade="all, delete-orphan")

class SocialLink(Base):
    __tablename__ = "social_links"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    platform_name: Mapped[str] = mapped_column(String) # linkedin, twitter, etc.
    url: Mapped[str] = mapped_column(String)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)

    member: Mapped["Member"] = relationship(back_populates="social_links")

class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    session_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String) # user, assistant
    message_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    member: Mapped["Member"] = relationship(back_populates="conversation_history")

class ProfileCompleteness(Base):
    __tablename__ = "profile_completeness"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), unique=True)
    completeness_score: Mapped[float] = mapped_column(Integer) # 0-100
    missing_fields: Mapped[dict] = mapped_column(JSON) # List of missing fields
    assessment: Mapped[Optional[str]] = mapped_column(Text) # LLM-generated assessment text
    last_calculated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    member: Mapped["Member"] = relationship(back_populates="profile_completeness")


class ProfileSuggestion(Base):
    __tablename__ = "profile_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    session_id: Mapped[str] = mapped_column(String, index=True)
    field_name: Mapped[str] = mapped_column(String)  # e.g., "bio", "role", "skills"
    current_value: Mapped[Optional[str]] = mapped_column(Text)
    suggested_value: Mapped[str] = mapped_column(Text)
    reasoning: Mapped[Optional[str]] = mapped_column(Text)  # Why this suggestion was made
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, accepted, rejected, edited
    accepted_value: Mapped[Optional[str]] = mapped_column(Text)  # What was actually published (if edited)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    member: Mapped["Member"] = relationship(back_populates="profile_suggestions")


Member.profile_suggestions = relationship("ProfileSuggestion", back_populates="member", cascade="all, delete-orphan")
Member.question_decks = relationship("QuestionDeck", back_populates="member", cascade="all, delete-orphan")
Member.question_responses = relationship("QuestionResponse", back_populates="member", cascade="all, delete-orphan")


class QuestionDeck(Base):
    """A collection of questions, either global or member-specific."""
    __tablename__ = "question_decks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    deck_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # NULL member_id = global deck; set member_id = personalized deck
    member_id: Mapped[Optional[int]] = mapped_column(ForeignKey("members.id"), nullable=True, index=True)

    # Metadata about deck generation
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    generation_context: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    questions: Mapped[List["Question"]] = relationship(back_populates="deck", cascade="all, delete-orphan")
    member: Mapped[Optional["Member"]] = relationship(back_populates="question_decks")


class Question(Base):
    """An individual question within a deck."""
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4)
    deck_id: Mapped[int] = mapped_column(ForeignKey("question_decks.id"))

    # Question content
    question_text: Mapped[str] = mapped_column(Text)
    category: Mapped[QuestionCategory] = mapped_column(Enum(QuestionCategory))
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), default=QuestionType.FREE_FORM)

    # Type-specific content
    options: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=list)  # For multiple_choice
    blank_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # For fill_in_blank (e.g., "My favorite way to unwind is ___")

    # For gamification and engagement
    difficulty_level: Mapped[int] = mapped_column(Integer, default=1)  # 1-3: easy, medium, deep
    estimated_time_minutes: Mapped[int] = mapped_column(Integer, default=2)

    # Purpose and context
    purpose: Mapped[str] = mapped_column(Text)
    follow_up_prompts: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=list)
    potential_insights: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=list)
    related_profile_fields: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)

    # NEW: Graph-aware targeting context
    relevant_member_ids: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer), default=list)  # Members this question is about
    notes: Mapped[Optional[str]] = mapped_column(Text)  # Why we're asking this (context for display)
    edge_context: Mapped[Optional[dict]] = mapped_column(JSON)  # {edge_id, edge_type, connected_member_name}
    targeting_criteria: Mapped[Optional[dict]] = mapped_column(JSON)  # {pattern_ids, skill_match, randomness_weight}
    vibe: Mapped[Optional[QuestionVibe]] = mapped_column(Enum(QuestionVibe), nullable=True)  # Tone of the question

    # Ordering and status
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    deck: Mapped["QuestionDeck"] = relationship(back_populates="questions")
    responses: Mapped[List["QuestionResponse"]] = relationship(back_populates="question", cascade="all, delete-orphan")


class QuestionResponse(Base):
    """A member's response to a question."""
    __tablename__ = "question_responses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    session_id: Mapped[str] = mapped_column(String, index=True)

    response_text: Mapped[str] = mapped_column(Text)

    # Did this question lead to useful profile data?
    led_to_suggestion: Mapped[bool] = mapped_column(Boolean, default=False)
    suggestion_id: Mapped[Optional[int]] = mapped_column(ForeignKey("profile_suggestions.id"), nullable=True)

    # Engagement metrics for deck refinement
    engagement_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5 from member

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    question: Mapped["Question"] = relationship(back_populates="responses")
    member: Mapped["Member"] = relationship(back_populates="question_responses")


class Pattern(Base):
    """Discovered patterns in community member data."""
    __tablename__ = "patterns"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[PatternCategory] = mapped_column(Enum(PatternCategory), index=True)

    # Evidence and context
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    related_member_ids: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer), default=list)
    evidence: Mapped[Optional[dict]] = mapped_column(JSON)

    # For question generation
    question_prompts: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=list)

    # Graph metadata (new)
    edge_count: Mapped[int] = mapped_column(Integer, default=0)  # How many edges created from this pattern
    question_count: Mapped[int] = mapped_column(Integer, default=0)  # Questions generated from this
    last_question_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    vitality_score: Mapped[float] = mapped_column(Integer, default=50)  # 0-100, how "alive" this pattern is

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


# =============================================================================
# GRAPH SYSTEM MODELS (Wave 1)
# =============================================================================

class MemberEdge(Base):
    """Connections between members in the community graph."""
    __tablename__ = "member_edges"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # The two connected members
    member_a_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)
    member_b_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)

    # Edge properties
    edge_type: Mapped[EdgeType] = mapped_column(Enum(EdgeType), index=True)
    strength: Mapped[float] = mapped_column(Integer, default=50)  # 0-100 (stored as int for simplicity)
    discovered_via: Mapped[str] = mapped_column(String(100))  # "pattern_finder", "question_response", "event_signal", etc.

    # Evidence of why this edge exists
    evidence: Mapped[Optional[dict]] = mapped_column(JSON)  # {pattern_id, question_id, shared_skills, notes}

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    member_a: Mapped["Member"] = relationship(foreign_keys=[member_a_id], backref="edges_as_a")
    member_b: Mapped["Member"] = relationship(foreign_keys=[member_b_id], backref="edges_as_b")


class TasteProfile(Base):
    """Evolving taste/preference profile for a member."""
    __tablename__ = "taste_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), unique=True, index=True)

    # Explicit preferences (from interviews/conversations)
    vibe_words: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)  # ["cozy", "weird", "intimate"]
    avoid_words: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)  # ["crowded", "loud"]
    energy_time: Mapped[Optional[str]] = mapped_column(String(50))  # "morning", "afternoon", "evening", "night"
    usual_company: Mapped[Optional[str]] = mapped_column(String(50))  # "solo", "duo", "group", "varies"
    spontaneity: Mapped[int] = mapped_column(Integer, default=50)  # 0 (planner) to 100 (spontaneous)

    # Anti-preferences (dealbreakers) - underrated!
    dealbreakers: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)  # ["standing room", "cash only"]
    not_my_thing: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)  # Things they just don't get

    # Implicit preferences (learned from behavior) - JSON for flexibility
    category_affinities: Mapped[Optional[dict]] = mapped_column(JSON)  # {"Live Music": 80, "Workshops": 30}
    venue_affinities: Mapped[Optional[dict]] = mapped_column(JSON)  # {"Varsity Theatre": 90}
    organizer_affinities: Mapped[Optional[dict]] = mapped_column(JSON)  # {"Ashland Folk Collective": 80}
    price_comfort: Mapped[Optional[dict]] = mapped_column(JSON)  # {"min": 0, "max": 50, "sweet_spot": 15}

    # Contextual state (temporary)
    current_mood: Mapped[Optional[str]] = mapped_column(String(100))
    this_week_energy: Mapped[Optional[str]] = mapped_column(String(50))  # "low", "medium", "high"
    visitors_in_town: Mapped[bool] = mapped_column(Boolean, default=False)
    context_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationship
    member: Mapped["Member"] = relationship(backref="taste_profile")


class EventSignal(Base):
    """Tracks member interactions with Rova events for behavioral learning."""
    __tablename__ = "event_signals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)

    # Rova event reference
    rova_event_id: Mapped[str] = mapped_column(String(100), index=True)  # "event.xxx"
    rova_event_slug: Mapped[str] = mapped_column(String(255))

    # Signal type and strength
    signal_type: Mapped[SignalType] = mapped_column(Enum(SignalType), index=True)
    signal_strength: Mapped[int] = mapped_column(Integer)  # 100 for attended, 50 for RSVP, -30 for skipped

    # Denormalized event context for analysis (avoid joins)
    event_category: Mapped[Optional[str]] = mapped_column(String(100))
    event_venue_slug: Mapped[Optional[str]] = mapped_column(String(255))
    event_organizer_slug: Mapped[Optional[str]] = mapped_column(String(255))
    event_tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    event_time_of_day: Mapped[Optional[str]] = mapped_column(String(50))  # "morning", "afternoon", "evening", "night"
    event_day_of_week: Mapped[Optional[str]] = mapped_column(String(20))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    member: Mapped["Member"] = relationship(backref="event_signals")


class QuestionDelivery(Base):
    """Tracks multi-channel question delivery and responses."""
    __tablename__ = "question_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)

    # Delivery info
    channel: Mapped[DeliveryChannel] = mapped_column(Enum(DeliveryChannel), index=True)
    delivery_status: Mapped[DeliveryStatus] = mapped_column(Enum(DeliveryStatus), default=DeliveryStatus.PENDING)

    # Timestamps for funnel analysis
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Response data
    response_type: Mapped[Optional[str]] = mapped_column(String(50))  # "yes", "no", "skip", "text", "choice"
    response_value: Mapped[Optional[str]] = mapped_column(Text)
    response_time_seconds: Mapped[Optional[int]] = mapped_column(Integer)  # How long they took

    # Why this question was selected for this member
    targeting_context: Mapped[Optional[dict]] = mapped_column(JSON)  # {pattern_id, edge_id, relevance_score}

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    question: Mapped["Question"] = relationship(backref="deliveries")
    member: Mapped["Member"] = relationship(backref="question_deliveries")
