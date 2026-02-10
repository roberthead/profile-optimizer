"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Member,
    QuestionDeck,
    Question,
    QuestionCategory,
    Pattern,
    PatternCategory,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session():
    """Create a mock database session for unit tests."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def sample_member():
    """Create a sample member for testing."""
    member = MagicMock(spec=Member)
    member.id = 1
    member.email = "test@example.com"
    member.first_name = "Test"
    member.last_name = "User"
    member.bio = "I am a software developer who loves building things."
    member.role = "Software Engineer"
    member.company = "Test Corp"
    member.location = "Portland, OR"
    member.website = "https://example.com"
    member.skills = ["Python", "React", "PostgreSQL"]
    member.interests = ["AI", "Music", "Open Source"]
    member.prompt_responses = ["I joined because I love the community."]
    member.membership_status = "active_create"
    return member


@pytest.fixture
def sample_member_with_gaps():
    """Create a sample member with profile gaps for testing."""
    member = MagicMock(spec=Member)
    member.id = 2
    member.email = "gaps@example.com"
    member.first_name = "Gap"
    member.last_name = "User"
    member.bio = None
    member.role = None
    member.company = None
    member.location = None
    member.website = None
    member.skills = None
    member.interests = None
    member.prompt_responses = None
    member.membership_status = "active_create"
    return member


@pytest.fixture
def sample_members(sample_member, sample_member_with_gaps):
    """Create a list of sample members for testing."""
    # Create a few more members with varying completeness
    member3 = MagicMock(spec=Member)
    member3.id = 3
    member3.email = "partial@example.com"
    member3.first_name = "Partial"
    member3.last_name = "Profile"
    member3.bio = "Short bio"
    member3.role = "Designer"
    member3.company = None
    member3.location = "San Francisco"
    member3.website = None
    member3.skills = ["UX", "Figma"]
    member3.interests = None
    member3.prompt_responses = None
    member3.membership_status = "active_create"

    return [sample_member, sample_member_with_gaps, member3]


@pytest.fixture
def sample_question_deck():
    """Create a sample question deck for testing."""
    deck = MagicMock(spec=QuestionDeck)
    deck.id = 1
    deck.name = "Test Deck"
    deck.description = "A test deck for unit tests"
    deck.member_id = None
    deck.is_active = True
    deck.version = 1
    return deck


@pytest.fixture
def sample_questions():
    """Create sample questions for testing."""
    questions = []
    for i, (category, text) in enumerate(
        [
            (QuestionCategory.ORIGIN_STORY, "What brought you to this community?"),
            (QuestionCategory.CREATIVE_SPARK, "What project are you most proud of?"),
            (
                QuestionCategory.COLLABORATION,
                "What kind of collaborator are you looking for?",
            ),
        ]
    ):
        q = MagicMock(spec=Question)
        q.id = i + 1
        q.question_text = text
        q.category = category
        q.difficulty_level = (i % 3) + 1
        q.purpose = f"Purpose for question {i + 1}"
        q.follow_up_prompts = ["Tell me more"]
        q.potential_insights = ["Insight 1"]
        q.related_profile_fields = ["bio"]
        q.order_index = i
        questions.append(q)
    return questions


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client for testing."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_pattern():
    """Create a sample pattern for testing."""
    pattern = MagicMock(spec=Pattern)
    pattern.id = 1
    pattern.name = "Creative Technologists"
    pattern.description = "Members combining technical and creative skills"
    pattern.category = PatternCategory.SKILL_CLUSTER
    pattern.member_count = 5
    pattern.related_member_ids = [1, 2, 3]
    pattern.evidence = {"skills": ["Python", "Design"]}
    pattern.question_prompts = ["What inspires your creative work?"]
    pattern.is_active = True
    return pattern
