"""Tests for the PatternFinderAgent and related tools."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.tools.question_tools import (
    save_pattern,
    SAVE_PATTERN_TOOL,
)
from app.agents.pattern_finder import PatternFinderAgent
from app.models import PatternCategory


class TestSavePatternTool:
    """Tests for the save_pattern function."""

    @pytest.mark.asyncio
    async def test_save_pattern_creates_new_pattern(self, mock_db_session):
        """Test that save_pattern creates a new pattern."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        mock_db_session.add = MagicMock()

        pattern_data = {
            "name": "Creative Technologists",
            "description": "Members who combine technical and creative skills",
            "category": "skill_cluster",
            "member_count": 5,
            "related_member_ids": [1, 2, 3],
            "evidence": {"skills": ["Python", "Design"]},
            "question_prompts": ["What inspires your creative work?"],
        }

        result = await save_pattern(mock_db_session, pattern_data)

        assert "error" not in result
        assert result["created"] is True
        assert result["updated"] is False
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_pattern_updates_existing_pattern(
        self, mock_db_session, sample_pattern
    ):
        """Test that save_pattern updates an existing pattern."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_pattern
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        pattern_data = {
            "name": "Creative Technologists",
            "description": "Updated description",
            "category": "skill_cluster",
            "member_count": 7,
        }

        result = await save_pattern(mock_db_session, pattern_data)

        assert "error" not in result
        assert result["created"] is False
        assert result["updated"] is True
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_pattern_requires_name(self, mock_db_session):
        """Test that save_pattern requires a name."""
        pattern_data = {
            "description": "No name provided",
            "category": "skill_cluster",
            "member_count": 3,
        }

        result = await save_pattern(mock_db_session, pattern_data)

        assert "error" in result
        assert "name" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_save_pattern_validates_category(self, mock_db_session):
        """Test that save_pattern validates category enum."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        pattern_data = {
            "name": "Test Pattern",
            "description": "Test",
            "category": "invalid_category",
            "member_count": 3,
        }

        result = await save_pattern(mock_db_session, pattern_data)

        assert "error" in result
        assert "invalid_category" in result["error"].lower()

    def test_save_pattern_tool_schema(self):
        """Test that SAVE_PATTERN_TOOL has correct schema."""
        assert "name" in SAVE_PATTERN_TOOL
        assert "description" in SAVE_PATTERN_TOOL
        assert "input_schema" in SAVE_PATTERN_TOOL

        schema = SAVE_PATTERN_TOOL["input_schema"]
        props = schema["properties"]

        assert "name" in props
        assert "description" in props
        assert "category" in props
        assert "member_count" in props
        assert "related_member_ids" in props
        assert "evidence" in props
        assert "question_prompts" in props

        # Check category enum values
        assert props["category"]["type"] == "string"
        assert "enum" in props["category"]
        expected_categories = [
            "skill_cluster",
            "interest_theme",
            "collaboration_opportunity",
            "community_strength",
            "cross_domain",
        ]
        assert sorted(props["category"]["enum"]) == sorted(expected_categories)


class TestPatternFinderAgent:
    """Tests for the PatternFinderAgent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_db_session):
        """Test that agent initializes correctly."""
        with patch("app.agents.pattern_finder.anthropic.Anthropic"):
            agent = PatternFinderAgent(mock_db_session)
            assert agent.db == mock_db_session
            assert agent.model == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_execute_tool_community_analysis(
        self, mock_db_session, sample_members
    ):
        """Test that _execute_tool handles community analysis correctly."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_members
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.agents.pattern_finder.anthropic.Anthropic"):
            agent = PatternFinderAgent(mock_db_session)
            result_dict = {
                "success": False,
                "patterns_found": 0,
                "patterns": [],
                "response_text": "",
            }

            tool_result = await agent._execute_tool(
                "get_community_profile_analysis", {}, result_dict
            )

            assert "total_active_members" in tool_result
            assert tool_result["total_active_members"] == 3

    @pytest.mark.asyncio
    async def test_execute_tool_save_pattern(self, mock_db_session):
        """Test that _execute_tool handles save_pattern correctly."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        mock_db_session.add = MagicMock()

        with patch("app.agents.pattern_finder.anthropic.Anthropic"):
            agent = PatternFinderAgent(mock_db_session)
            result_dict = {
                "success": False,
                "patterns_found": 0,
                "patterns": [],
                "response_text": "",
            }

            pattern_input = {
                "name": "Test Pattern",
                "description": "Test description",
                "category": "skill_cluster",
                "member_count": 3,
            }

            tool_result = await agent._execute_tool(
                "save_pattern", pattern_input, result_dict
            )

            assert "error" not in tool_result
            assert result_dict["patterns_found"] == 1
            assert len(result_dict["patterns"]) == 1

    @pytest.mark.asyncio
    async def test_execute_tool_save_pattern_error(self, mock_db_session):
        """Test that _execute_tool handles save_pattern errors correctly."""
        with patch("app.agents.pattern_finder.anthropic.Anthropic"):
            agent = PatternFinderAgent(mock_db_session)
            result_dict = {
                "success": False,
                "patterns_found": 0,
                "patterns": [],
                "response_text": "",
            }

            # Missing name should cause error
            pattern_input = {
                "description": "Test description",
                "category": "skill_cluster",
                "member_count": 3,
            }

            tool_result = await agent._execute_tool(
                "save_pattern", pattern_input, result_dict
            )

            assert "error" in tool_result
            # Should not increment patterns_found on error
            assert result_dict["patterns_found"] == 0
            assert len(result_dict["patterns"]) == 0

    @pytest.mark.asyncio
    async def test_execute_tool_unknown_tool(self, mock_db_session):
        """Test that _execute_tool handles unknown tools."""
        with patch("app.agents.pattern_finder.anthropic.Anthropic"):
            agent = PatternFinderAgent(mock_db_session)
            result_dict = {
                "success": False,
                "patterns_found": 0,
                "patterns": [],
                "response_text": "",
            }

            tool_result = await agent._execute_tool("unknown_tool", {}, result_dict)

            assert "error" in tool_result
            assert "unknown_tool" in tool_result["error"].lower()


class TestPatternCategory:
    """Tests for PatternCategory enum."""

    def test_all_categories_defined(self):
        """Test that all expected categories are defined."""
        expected = [
            "skill_cluster",
            "interest_theme",
            "collaboration_opportunity",
            "community_strength",
            "cross_domain",
        ]

        actual = [c.value for c in PatternCategory]
        assert sorted(actual) == sorted(expected)

    def test_category_values_are_strings(self):
        """Test that category values are strings for JSON serialization."""
        for category in PatternCategory:
            assert isinstance(category.value, str)

    def test_category_can_be_created_from_string(self):
        """Test that categories can be created from string values."""
        for category in PatternCategory:
            recreated = PatternCategory(category.value)
            assert recreated == category
