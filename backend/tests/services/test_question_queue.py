"""Tests for the QuestionQueueBuilder service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Member,
    Pattern,
    PatternCategory,
    Question,
    QuestionCategory,
    QuestionType,
)
from app.services.question_queue import QuestionQueueBuilder, ScoredQuestion


# ---- Fixtures ----


def make_member(
    id=1,
    first_name="Test",
    last_name="User",
    email="test@example.com",
    bio="I am a software developer who loves building things and working with teams.",
    role="Software Engineer",
    company="Test Corp",
    location="Portland, OR",
    website="https://example.com",
    skills=None,
    interests=None,
    prompt_responses=None,
):
    member = MagicMock(spec=Member)
    member.id = id
    member.first_name = first_name
    member.last_name = last_name
    member.email = email
    member.bio = bio
    member.role = role
    member.company = company
    member.location = location
    member.website = website
    member.skills = skills if skills is not None else ["Python", "React", "PostgreSQL"]
    member.interests = (
        interests if interests is not None else ["AI", "Music", "Open Source"]
    )
    member.prompt_responses = (
        prompt_responses
        if prompt_responses is not None
        else ["I joined because I love the community."]
    )
    return member


def make_pattern(
    id=1,
    name="Creative Technologists",
    category=PatternCategory.SKILL_CLUSTER,
    member_count=5,
    related_member_ids=None,
    evidence=None,
    is_active=True,
):
    pattern = MagicMock(spec=Pattern)
    pattern.id = id
    pattern.name = name
    pattern.category = category
    pattern.member_count = member_count
    pattern.related_member_ids = related_member_ids or []
    pattern.evidence = evidence or {"skills": ["Python", "Design"]}
    pattern.is_active = is_active
    return pattern


def make_question(
    id=1,
    text="What brought you here?",
    category=QuestionCategory.ORIGIN_STORY,
    question_type=QuestionType.FREE_FORM,
    difficulty=1,
    related_profile_fields=None,
    related_pattern_ids=None,
    options=None,
    blank_prompt=None,
    is_active=True,
):
    q = MagicMock(spec=Question)
    q.id = id
    q.question_text = text
    q.category = category
    q.question_type = question_type
    q.difficulty_level = difficulty
    q.related_profile_fields = related_profile_fields or []
    q.related_pattern_ids = related_pattern_ids or []
    q.options = options or []
    q.blank_prompt = blank_prompt
    q.is_active = is_active
    return q


# ---- Helper to mock DB queries ----


def setup_mock_db(
    member=None,
    patterns=None,
    answered_ids=None,
    questions=None,
):
    """Set up a mock AsyncSession that returns the specified data."""
    db = AsyncMock(spec=AsyncSession)
    patterns = patterns or []
    answered_ids = answered_ids or []
    questions = questions or []

    call_count = {"n": 0}

    async def mock_execute(query):
        result = MagicMock()
        idx = call_count["n"]
        call_count["n"] += 1

        if idx == 0:
            # _load_member
            result.scalar_one_or_none.return_value = member
        elif idx == 1:
            # _load_active_patterns
            result.scalars.return_value.all.return_value = patterns
        elif idx == 2:
            # _load_answered_question_ids
            result.scalars.return_value.all.return_value = list(answered_ids)
        elif idx == 3:
            # _load_available_questions
            result.scalars.return_value.all.return_value = questions
        return result

    db.execute = mock_execute
    return db


# ---- Tests ----


class TestQuestionQueueBuilder:
    @pytest.mark.asyncio
    async def test_member_not_found_returns_none(self):
        db = setup_mock_db(member=None)
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_queue_all_answered(self):
        member = make_member()
        db = setup_mock_db(member=member, questions=[])
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(1)

        assert result is not None
        assert result["member_id"] == 1
        assert result["queue"] == []
        assert result["scoring_summary"]["total_available"] == 0

    @pytest.mark.asyncio
    async def test_basic_scoring_with_profile_gaps(self):
        """Questions targeting profile gaps should get profile_gap score."""
        member = make_member(bio=None, role=None, skills=[])

        q1 = make_question(
            id=1, text="Tell us about yourself", related_profile_fields=["bio"]
        )
        q2 = make_question(
            id=2, text="What do you do?", related_profile_fields=["role"]
        )
        q3 = make_question(id=3, text="Random question")

        db = setup_mock_db(member=member, questions=[q1, q2, q3])
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(1)

        assert len(result["queue"]) == 3
        # Questions with profile gap targets should score higher
        scores = {q["question_id"]: q["score"] for q in result["queue"]}
        assert scores[1] > scores[3]
        assert scores[2] > scores[3]

    @pytest.mark.asyncio
    async def test_pattern_probe_scoring(self):
        """Questions probing a high-affinity pattern should get high scores."""
        member = make_member(skills=["Python", "React"], interests=["AI"])

        # Pattern the member is NOT in, but has high affinity
        pattern = make_pattern(
            id=10,
            name="AI Builders",
            related_member_ids=[2, 3],  # member 1 not in this pattern
            evidence={
                "skills": ["Python", "TensorFlow"],
                "interests": ["AI", "Machine Learning"],
            },
        )

        q1 = make_question(
            id=1, text="How do you use AI?", related_pattern_ids=[10], difficulty=2
        )
        q2 = make_question(id=2, text="Generic question")

        db = setup_mock_db(member=member, patterns=[pattern], questions=[q1, q2])
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(1)

        scores = {q["question_id"]: q for q in result["queue"]}
        assert scores[1]["score"] > scores[2]["score"]
        assert scores[1]["reason"] == "pattern_probe"

    @pytest.mark.asyncio
    async def test_pattern_deepen_scoring(self):
        """Questions deepening a pattern the member IS in should score well."""
        member = make_member()

        pattern = make_pattern(
            id=5,
            name="Creative Technologists",
            related_member_ids=[1, 2, 3],  # member 1 IS in this pattern
        )

        q1 = make_question(
            id=1, text="What inspires your tech+art work?", related_pattern_ids=[5]
        )
        q2 = make_question(id=2, text="Generic question")

        db = setup_mock_db(member=member, patterns=[pattern], questions=[q1, q2])
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(1)

        scores = {q["question_id"]: q for q in result["queue"]}
        assert scores[1]["score"] > scores[2]["score"]
        assert scores[1]["reason"] == "pattern_deepen"

    @pytest.mark.asyncio
    async def test_additive_scoring(self):
        """A question with both pattern probe and profile gap should get both scores."""
        member = make_member(bio=None, skills=["Python"], interests=["AI"])

        pattern = make_pattern(
            id=10,
            related_member_ids=[2, 3],
            evidence={"skills": ["Python"], "interests": ["AI"]},
        )

        q1 = make_question(
            id=1,
            text="Multi-signal question",
            related_pattern_ids=[10],
            related_profile_fields=["bio"],
        )

        db = setup_mock_db(member=member, patterns=[pattern], questions=[q1])
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(1)

        q = result["queue"][0]
        # Should have pattern_probe (10.0 * affinity) + profile_gap (4.0) + minimum (0.1)
        assert q["score"] > 10.0  # at least probe + gap

    @pytest.mark.asyncio
    async def test_fallback_scoring(self):
        """Questions with profile fields but no pattern link get fallback score."""
        member = make_member()

        q1 = make_question(
            id=1, text="Question with fields", related_profile_fields=["skills"]
        )

        db = setup_mock_db(member=member, questions=[q1])
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(1)

        q = result["queue"][0]
        assert q["reason"] == "fallback"
        assert q["score"] >= 1.0

    @pytest.mark.asyncio
    async def test_sequencing_order(self):
        """Queue should sequence: easy first, medium middle, deep last."""
        member = make_member(bio=None, role=None)

        questions = [
            make_question(
                id=i, text=f"Q{i}", difficulty=d, related_profile_fields=["bio"]
            )
            for i, d in [
                (1, 3),
                (2, 1),
                (3, 2),
                (4, 1),
                (5, 2),
                (6, 3),
                (7, 1),
                (8, 2),
                (9, 3),
                (10, 2),
            ]
        ]

        db = setup_mock_db(member=member, questions=questions)
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(1)

        queue = result["queue"]
        assert len(queue) == 10

        # First 3 should prefer easy (difficulty 1)
        # Middle should prefer medium (difficulty 2)
        # Last should prefer deep (difficulty 3)
        # (exact assignment depends on score ties, but the structure should hold)
        early_diffs = [q["difficulty"] for q in queue[:3]]
        # At least some easy questions should be in the front
        assert 1 in early_diffs

    @pytest.mark.asyncio
    async def test_member_no_skills_interests(self):
        """Member with no skills/interests should get fallback/gap-focused queue."""
        member = make_member(skills=[], interests=[], bio=None, role=None)

        pattern = make_pattern(
            id=10,
            related_member_ids=[2],
            evidence={"skills": ["Python"], "interests": ["AI"]},
        )

        q1 = make_question(
            id=1, text="Q1", related_pattern_ids=[10], related_profile_fields=["bio"]
        )
        q2 = make_question(id=2, text="Q2", related_profile_fields=["role"])

        db = setup_mock_db(member=member, patterns=[pattern], questions=[q1, q2])
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(1)

        # All pattern affinities should be 0 since member has no skills/interests
        assert len(result["scoring_summary"]["high_affinity_patterns"]) == 0
        assert len(result["queue"]) == 2

    @pytest.mark.asyncio
    async def test_evidence_key_variants(self):
        """Pattern evidence with skill_names key should work like skills key."""
        member = make_member(skills=["Python", "Design"])

        pattern = make_pattern(
            id=10,
            related_member_ids=[2],
            evidence={"skill_names": ["Python", "Design", "React"]},
        )

        q1 = make_question(id=1, text="Q1", related_pattern_ids=[10])

        db = setup_mock_db(member=member, patterns=[pattern], questions=[q1])
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(1)

        # Should have computed affinity since skill_names variant is supported
        assert len(result["scoring_summary"]["high_affinity_patterns"]) > 0

    @pytest.mark.asyncio
    async def test_queue_max_10(self):
        """Queue should return at most 10 questions."""
        member = make_member()

        questions = [
            make_question(id=i, text=f"Q{i}", related_profile_fields=["bio"])
            for i in range(1, 21)
        ]

        db = setup_mock_db(member=member, questions=questions)
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(1)

        assert len(result["queue"]) == 10

    @pytest.mark.asyncio
    async def test_fewer_than_10_questions(self):
        """Queue works with fewer than 10 available questions."""
        member = make_member()

        questions = [make_question(id=i, text=f"Q{i}") for i in range(1, 4)]

        db = setup_mock_db(member=member, questions=questions)
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(1)

        assert len(result["queue"]) == 3

    @pytest.mark.asyncio
    async def test_scoring_summary(self):
        """Scoring summary should include correct metadata."""
        member = make_member(bio=None)

        pattern_in = make_pattern(id=5, related_member_ids=[1, 2])
        pattern_close = make_pattern(
            id=10,
            related_member_ids=[2, 3],
            evidence={"skills": ["Python", "React"]},
        )

        q1 = make_question(id=1, text="Q1")

        db = setup_mock_db(
            member=member, patterns=[pattern_in, pattern_close], questions=[q1]
        )
        builder = QuestionQueueBuilder(db)
        result = await builder.build_queue(1)

        summary = result["scoring_summary"]
        assert summary["total_available"] == 1
        assert summary["already_answered"] == 0
        assert summary["pattern_memberships"] == 1
        assert len(summary["profile_gaps"]) > 0
        # pattern_close should show as high affinity
        assert any(p["id"] == 10 for p in summary["high_affinity_patterns"])


class TestProfileGapDetection:
    def test_full_profile_no_gaps(self):
        member = make_member()
        gaps = QuestionQueueBuilder._detect_profile_gaps(member)
        assert len(gaps) == 0

    def test_empty_profile_all_gaps(self):
        member = make_member(
            bio=None,
            role=None,
            company=None,
            location=None,
            website=None,
            skills=[],
            interests=[],
            prompt_responses=[],
        )
        gaps = QuestionQueueBuilder._detect_profile_gaps(member)
        gap_fields = {g["field"] for g in gaps}
        assert "bio" in gap_fields
        assert "role" in gap_fields
        assert "company" in gap_fields
        assert "location" in gap_fields
        assert "website" in gap_fields
        assert "skills" in gap_fields
        assert "interests" in gap_fields
        assert "prompt_responses" in gap_fields

    def test_short_bio_is_gap(self):
        member = make_member(bio="Short")
        gaps = QuestionQueueBuilder._detect_profile_gaps(member)
        assert any(g["field"] == "bio" for g in gaps)

    def test_few_skills_is_gap(self):
        member = make_member(skills=["Python"])
        gaps = QuestionQueueBuilder._detect_profile_gaps(member)
        assert any(g["field"] == "skills" for g in gaps)


class TestSequencing:
    def test_sequence_prefers_difficulty_order(self):
        """Easy questions first, deep questions last."""
        questions = [
            ScoredQuestion(
                question_id=i,
                question_text=f"Q{i}",
                question_type="free_form",
                category="origin_story",
                difficulty=d,
                options=[],
                blank_prompt=None,
                score=5.0,
                reason=r,
            )
            for i, d, r in [
                (1, 3, "pattern_deepen"),
                (2, 1, "profile_gap"),
                (3, 2, "pattern_probe"),
                (4, 1, "profile_gap"),
                (5, 2, "pattern_probe"),
                (6, 3, "pattern_deepen"),
            ]
        ]
        result = QuestionQueueBuilder._sequence(questions)
        assert len(result) == 6
        # First items should prefer easy/gap
        assert result[0].difficulty == 1

    def test_sequence_empty_list(self):
        result = QuestionQueueBuilder._sequence([])
        assert result == []
