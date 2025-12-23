"""Tests for the QuestionDeckAgent and related tools."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.question_tools import (
    get_community_profile_analysis,
    get_member_gaps,
    GET_COMMUNITY_ANALYSIS_TOOL,
    GET_MEMBER_GAPS_TOOL,
    SAVE_QUESTION_DECK_TOOL,
)
from app.agents.question_deck import QuestionDeckAgent
from app.models import Member, QuestionDeck, Question, QuestionCategory


class TestQuestionTools:
    """Tests for question generation tools."""

    @pytest.mark.asyncio
    async def test_get_community_profile_analysis_structure(self, mock_db_session, sample_members):
        """Test that community analysis returns expected structure."""
        # Setup mock to return sample members
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_members
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await get_community_profile_analysis(mock_db_session)

        # Verify structure
        assert "total_active_members" in result
        assert "field_completion_rates" in result
        assert "common_skills" in result
        assert "common_interests" in result
        assert "unique_skills" in result
        assert "unique_interests" in result

    @pytest.mark.asyncio
    async def test_get_community_profile_analysis_counts_fields(self, mock_db_session, sample_members):
        """Test that community analysis correctly counts field completion."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_members
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await get_community_profile_analysis(mock_db_session)

        assert result["total_active_members"] == 3
        rates = result["field_completion_rates"]

        # Check that bio rate is calculated correctly (2 out of 3 have bios)
        assert rates["bio"]["filled"] == 2
        assert rates["bio"]["total"] == 3

    @pytest.mark.asyncio
    async def test_get_community_profile_analysis_aggregates_skills(self, mock_db_session, sample_members):
        """Test that community analysis aggregates skills correctly."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_members
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await get_community_profile_analysis(mock_db_session)

        # Should have skills from multiple members
        common_skills = dict(result["common_skills"])
        assert "Python" in common_skills or "UX" in common_skills

    @pytest.mark.asyncio
    async def test_get_member_gaps_identifies_missing_fields(self, mock_db_session, sample_member_with_gaps):
        """Test that member gaps analysis identifies missing fields."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_member_with_gaps
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await get_member_gaps(mock_db_session, sample_member_with_gaps.id)

        assert result["member_id"] == sample_member_with_gaps.id
        assert len(result["gaps"]) > 0

        # Should identify bio as a gap
        gap_fields = [g["field"] for g in result["gaps"]]
        assert "bio" in gap_fields
        assert "skills" in gap_fields

    @pytest.mark.asyncio
    async def test_get_member_gaps_complete_profile(self, mock_db_session, sample_member):
        """Test that member gaps analysis works for complete profiles."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_member
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await get_member_gaps(mock_db_session, sample_member.id)

        assert result["member_id"] == sample_member.id
        # Complete profile should have fewer gaps
        assert len(result["gaps"]) == 0

    @pytest.mark.asyncio
    async def test_get_member_gaps_not_found(self, mock_db_session):
        """Test that member gaps analysis handles missing member."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await get_member_gaps(mock_db_session, 99999)

        assert "error" in result

    def test_tool_definitions_have_required_fields(self):
        """Test that tool definitions have all required fields for Claude API."""
        for tool in [GET_COMMUNITY_ANALYSIS_TOOL, GET_MEMBER_GAPS_TOOL, SAVE_QUESTION_DECK_TOOL]:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"

    def test_save_question_deck_tool_schema(self):
        """Test that save_question_deck tool has correct schema."""
        schema = SAVE_QUESTION_DECK_TOOL["input_schema"]
        props = schema["properties"]

        assert "name" in props
        assert "description" in props
        assert "questions" in props
        assert props["questions"]["type"] == "array"

        # Check question item schema
        question_props = props["questions"]["items"]["properties"]
        assert "question_text" in question_props
        assert "category" in question_props
        assert "purpose" in question_props


class TestQuestionDeckAgent:
    """Tests for the QuestionDeckAgent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_db_session):
        """Test that agent initializes correctly."""
        with patch('app.agents.question_deck.anthropic.Anthropic'):
            agent = QuestionDeckAgent(mock_db_session)
            assert agent.db == mock_db_session
            assert agent.model == "claude-opus-4-5"

    @pytest.mark.asyncio
    async def test_generate_personalized_deck_member_not_found(self, mock_db_session):
        """Test that personalized deck generation raises error for missing member."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch('app.agents.question_deck.anthropic.Anthropic'):
            agent = QuestionDeckAgent(mock_db_session)

            with pytest.raises(ValueError, match="not found"):
                await agent.generate_personalized_deck(member_id=99999)

    @pytest.mark.asyncio
    async def test_refine_deck_not_found(self, mock_db_session):
        """Test that refine deck raises error for missing deck."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch('app.agents.question_deck.anthropic.Anthropic'):
            agent = QuestionDeckAgent(mock_db_session)

            with pytest.raises(ValueError, match="not found"):
                await agent.refine_deck(deck_id=99999, feedback="test")

    @pytest.mark.asyncio
    async def test_execute_tool_community_analysis(self, mock_db_session, sample_members):
        """Test that _execute_tool handles community analysis correctly."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_members
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch('app.agents.question_deck.anthropic.Anthropic'):
            agent = QuestionDeckAgent(mock_db_session)
            result_dict = {"analysis_context": None}

            tool_result = await agent._execute_tool(
                "get_community_profile_analysis",
                {},
                result_dict
            )

            assert "total_active_members" in tool_result
            assert result_dict["analysis_context"] is not None

    @pytest.mark.asyncio
    async def test_execute_tool_member_gaps(self, mock_db_session, sample_member_with_gaps):
        """Test that _execute_tool handles member gaps correctly."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_member_with_gaps
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch('app.agents.question_deck.anthropic.Anthropic'):
            agent = QuestionDeckAgent(mock_db_session)
            result_dict = {}

            tool_result = await agent._execute_tool(
                "get_member_gaps",
                {"member_id": 2},
                result_dict
            )

            assert tool_result["member_id"] == 2
            assert "gaps" in tool_result

    @pytest.mark.asyncio
    async def test_execute_tool_unknown_tool(self, mock_db_session):
        """Test that _execute_tool handles unknown tools."""
        with patch('app.agents.question_deck.anthropic.Anthropic'):
            agent = QuestionDeckAgent(mock_db_session)
            result_dict = {}

            tool_result = await agent._execute_tool(
                "unknown_tool",
                {},
                result_dict
            )

            assert "error" in tool_result

    @pytest.mark.asyncio
    async def test_save_deck_creates_records(self, mock_db_session):
        """Test that _save_deck creates deck and question records."""
        mock_db_session.add = MagicMock()
        mock_db_session.flush = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        with patch('app.agents.question_deck.anthropic.Anthropic'):
            agent = QuestionDeckAgent(mock_db_session)

            tool_input = {
                "name": "Test Deck",
                "description": "Test description",
                "questions": [
                    {
                        "question_text": "What is your favorite color?",
                        "category": "origin_story",
                        "purpose": "Ice breaker",
                        "difficulty_level": 1,
                    },
                    {
                        "question_text": "What inspires you?",
                        "category": "creative_spark",
                        "purpose": "Understand motivation",
                    },
                ]
            }

            await agent._save_deck(tool_input)

            # Should have added deck + 2 questions = 3 add calls
            assert mock_db_session.add.call_count == 3
            mock_db_session.commit.assert_called_once()


class TestQuestionCategory:
    """Tests for QuestionCategory enum."""

    def test_all_categories_defined(self):
        """Test that all expected categories are defined."""
        expected = [
            "origin_story",
            "creative_spark",
            "collaboration",
            "future_vision",
            "community_connection",
            "hidden_depths",
            "impact_legacy",
        ]

        actual = [c.value for c in QuestionCategory]
        assert sorted(actual) == sorted(expected)

    def test_category_values_are_strings(self):
        """Test that category values are strings for JSON serialization."""
        for category in QuestionCategory:
            assert isinstance(category.value, str)
