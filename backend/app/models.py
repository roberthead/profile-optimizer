from enum import Enum as PyEnum
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List
import uuid
from app.core.database import Base


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

    FREE_FORM = "free_form"  # Open-ended text response
    MULTIPLE_CHOICE = "multiple_choice"  # Select from predefined options
    YES_NO = "yes_no"  # Simple yes/no question
    FILL_IN_BLANK = "fill_in_blank"  # Complete a sentence


class PatternCategory(str, PyEnum):
    """Categories for discovered community patterns."""

    SKILL_CLUSTER = "skill_cluster"  # Groups of related skills that appear together
    INTEREST_THEME = "interest_theme"  # Common interest areas/passions
    COLLABORATION_OPPORTUNITY = (
        "collaboration_opportunity"  # Complementary skills/potential partnerships
    )
    COMMUNITY_STRENGTH = "community_strength"  # Core competencies of the community
    CROSS_DOMAIN = "cross_domain"  # Interesting overlaps between different areas


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4
    )
    clerk_user_id: Mapped[str] = mapped_column(
        String, unique=True, index=True
    )  # Link to Clerk User
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String)
    last_name: Mapped[Optional[str]] = mapped_column(String)
    profile_photo_url: Mapped[Optional[str]] = mapped_column(String)

    # Profile Content
    bio: Mapped[Optional[str]] = mapped_column(Text)
    company: Mapped[Optional[str]] = mapped_column(String)
    role: Mapped[Optional[str]] = mapped_column(
        String
    )  # e.g. "Software Engineer", "Shift Companion"
    website: Mapped[Optional[str]] = mapped_column(String)
    location: Mapped[Optional[str]] = mapped_column(String)

    # Membership
    membership_status: Mapped[str] = mapped_column(
        String, default="free"
    )  # free, active_create, active_fellow, etc.
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)

    # Arrays stored as JSON (skills, interests, etc.)
    urls: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    roles: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String), default=list
    )  # Community roles
    prompt_responses: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), default=list
    )
    skills: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    interests: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    all_traits: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    # Relationships
    social_links: Mapped[List["SocialLink"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )
    conversation_history: Mapped[List["ConversationHistory"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )
    profile_completeness: Mapped[Optional["ProfileCompleteness"]] = relationship(
        back_populates="member", uselist=False, cascade="all, delete-orphan"
    )


class SocialLink(Base):
    __tablename__ = "social_links"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    platform_name: Mapped[str] = mapped_column(String)  # linkedin, twitter, etc.
    url: Mapped[str] = mapped_column(String)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)

    member: Mapped["Member"] = relationship(back_populates="social_links")


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    session_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String)  # user, assistant
    message_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    member: Mapped["Member"] = relationship(back_populates="conversation_history")


class ProfileCompleteness(Base):
    __tablename__ = "profile_completeness"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), unique=True)
    completeness_score: Mapped[float] = mapped_column(Integer)  # 0-100
    missing_fields: Mapped[dict] = mapped_column(JSON)  # List of missing fields
    assessment: Mapped[Optional[str]] = mapped_column(
        Text
    )  # LLM-generated assessment text
    last_calculated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    member: Mapped["Member"] = relationship(back_populates="profile_completeness")


class ProfileSuggestion(Base):
    __tablename__ = "profile_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    session_id: Mapped[str] = mapped_column(String, index=True)
    field_name: Mapped[str] = mapped_column(String)  # e.g., "bio", "role", "skills"
    current_value: Mapped[Optional[str]] = mapped_column(Text)
    suggested_value: Mapped[str] = mapped_column(Text)
    reasoning: Mapped[Optional[str]] = mapped_column(
        Text
    )  # Why this suggestion was made
    status: Mapped[str] = mapped_column(
        String, default="pending"
    )  # pending, accepted, rejected, edited
    accepted_value: Mapped[Optional[str]] = mapped_column(
        Text
    )  # What was actually published (if edited)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    member: Mapped["Member"] = relationship(back_populates="profile_suggestions")


Member.profile_suggestions = relationship(
    "ProfileSuggestion", back_populates="member", cascade="all, delete-orphan"
)
Member.question_decks = relationship(
    "QuestionDeck", back_populates="member", cascade="all, delete-orphan"
)
Member.question_responses = relationship(
    "QuestionResponse", back_populates="member", cascade="all, delete-orphan"
)


class QuestionDeck(Base):
    """A collection of questions, either global or member-specific."""

    __tablename__ = "question_decks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # NULL member_id = global deck; set member_id = personalized deck
    member_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("members.id"), nullable=True, index=True
    )

    # Metadata about deck generation
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    generation_context: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    # Relationships
    questions: Mapped[List["Question"]] = relationship(
        back_populates="deck", cascade="all, delete-orphan"
    )
    member: Mapped[Optional["Member"]] = relationship(back_populates="question_decks")


class Question(Base):
    """An individual question within a deck."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4
    )
    deck_id: Mapped[int] = mapped_column(ForeignKey("question_decks.id"))

    # Question content
    question_text: Mapped[str] = mapped_column(Text)
    category: Mapped[QuestionCategory] = mapped_column(Enum(QuestionCategory))
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType), default=QuestionType.FREE_FORM
    )

    # Type-specific content
    options: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), default=list
    )  # For multiple_choice
    blank_prompt: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # For fill_in_blank (e.g., "My favorite way to unwind is ___")

    # For gamification and engagement
    difficulty_level: Mapped[int] = mapped_column(
        Integer, default=1
    )  # 1-3: easy, medium, deep
    estimated_time_minutes: Mapped[int] = mapped_column(Integer, default=2)

    # Purpose and context
    purpose: Mapped[str] = mapped_column(Text)
<<<<<<< HEAD
    follow_up_prompts: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=list)
    potential_insights: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=list)
    related_profile_fields: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    related_pattern_ids: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer), default=list)
=======
    follow_up_prompts: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), default=list
    )
    potential_insights: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), default=list
    )
    related_profile_fields: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String), default=list
    )
>>>>>>> f61db06 (Add Makefile with validate target, configure ruff, fix all lint issues)

    # Ordering and status
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    deck: Mapped["QuestionDeck"] = relationship(back_populates="questions")
    responses: Mapped[List["QuestionResponse"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


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
    suggestion_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("profile_suggestions.id"), nullable=True
    )

    # Engagement metrics for deck refinement
    engagement_rating: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 1-5 from member

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

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
    related_member_ids: Mapped[Optional[List[int]]] = mapped_column(
        ARRAY(Integer), default=list
    )
    evidence: Mapped[Optional[dict]] = mapped_column(JSON)

    # For question generation
    question_prompts: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), default=list
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
