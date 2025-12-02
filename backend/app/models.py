from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List
import uuid
from app.core.database import Base
from pgvector.sqlalchemy import Vector

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
    last_calculated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    member: Mapped["Member"] = relationship(back_populates="profile_completeness")
