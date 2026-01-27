"""LLM-backed agent for discovering patterns in community member data."""

import json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
import anthropic

from app.core.config import settings
from app.tools.question_tools import (
    get_community_profile_analysis,
    get_active_patterns,
    save_pattern,
    GET_COMMUNITY_ANALYSIS_TOOL,
    SAVE_PATTERN_TOOL,
)


SYSTEM_PROMPT = """You are a community analyst for White Rabbit Ashland, a creative community focused on technology, entrepreneurship, and the arts.

Your task is to discover meaningful patterns in member data that reveal insights about the community. These patterns will help foster connections, inform event planning, and guide question generation for deeper profile enrichment.

## Pattern Categories

1. **skill_cluster** - Groups of related skills that frequently appear together
   Example: "Full-Stack Creators" - members with both technical (coding, data) and creative (design, writing) skills

2. **interest_theme** - Common passions or curiosities shared by multiple members
   Example: "Future of Work Explorers" - members interested in AI, remote work, and entrepreneurship

3. **collaboration_opportunity** - Complementary skills that could lead to powerful partnerships
   Example: "Technical + Storytelling Synergy" - developers who could partner with writers/content creators

4. **community_strength** - Core competencies where the community has deep collective expertise
   Example: "Design Thinking Powerhouse" - strong concentration of UX, product design, and visual design skills

5. **cross_domain** - Unexpected overlaps between different areas
   Example: "Arts + Engineering Bridge" - members combining music/art with technical/analytical skills

## What Makes a Good Pattern

- **Actionable**: Could lead to introductions, events, workshops, or collaborations
- **Non-obvious**: Reveals something beyond simple frequency counts
- **Community-building**: Strengthens connections between members
- **Specific**: Names actual skills, interests, or member characteristics

## Output Requirements

For each pattern you discover, you MUST call save_pattern with:
- **name**: A memorable, descriptive name (e.g., "Creative Technologists", "Ashland Arts Ecosystem")
- **description**: 2-3 sentences explaining what this pattern reveals and why it matters
- **category**: One of the five categories above
- **member_count**: How many members exhibit this pattern
- **related_member_ids**: CRITICAL - Array of numeric member IDs (the "id" field from member_profiles) who exhibit this pattern. Example: [1, 5, 12]. This enables the UI to show member names.
- **evidence**: Object with supporting data (skill names, interest names, frequencies)
- **question_prompts**: 2-3 questions that could explore this pattern further

## Analysis Approach

1. First, examine the skill and interest frequency data to identify clusters
2. Look at the full member profiles to find non-obvious connections
3. Consider which members could be introduced to each other based on complementary abilities
4. Identify what makes this community unique compared to generic professional networks
5. Generate 5-10 high-quality patterns (quality over quantity)

Remember: You're not just counting skills - you're discovering the hidden structure of a creative community."""


class PatternFinderAgent:
    """LLM-backed agent that discovers patterns in community member data."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def discover_patterns(self) -> dict[str, Any]:
        """
        Analyze member data and discover meaningful patterns.

        Returns:
            Dict with patterns_found count, pattern details, and response text.
        """
        user_message = """Please analyze the White Rabbit community and discover meaningful patterns.

First, use the get_community_profile_analysis tool to get full data on all community members including their skills, interests, traits, and profiles. Note: Each member profile includes an "id" field - you MUST use these IDs when saving patterns.

Then, analyze this data to discover 5-10 high-quality patterns. For each pattern you discover, use the save_pattern tool to persist it.

IMPORTANT: When calling save_pattern, you MUST include related_member_ids as an array of the numeric member IDs (from the "id" field in member_profiles) for members who exhibit the pattern. This is required for the UI to display member names.

Focus on patterns that are:
- Actionable (could lead to introductions or events)
- Non-obvious (go beyond simple frequency counts)
- Community-building (strengthen member connections)

After saving all patterns, summarize what you discovered."""

        return await self._execute_with_tools(user_message)

    async def refresh_patterns(self) -> dict[str, Any]:
        """
        Re-analyze all data and update existing patterns.

        This preserves existing patterns and updates them with fresh member data,
        rather than wiping and starting fresh.

        Returns:
            Dict with patterns_found count and response text.
        """
        # Fetch existing patterns to pass to the LLM
        existing_patterns = await get_active_patterns(self.db)

        # Build context about existing patterns
        pattern_context = ""
        if existing_patterns["total_patterns"] > 0:
            pattern_names = [p["name"] for p in existing_patterns["patterns"]]
            pattern_context = f"""

EXISTING PATTERNS TO UPDATE:
The following {existing_patterns['total_patterns']} patterns already exist. When you find members matching these themes, UPDATE the existing pattern by using the EXACT SAME NAME:
{json.dumps(pattern_names, indent=2)}

For each existing pattern, re-evaluate which members should be included based on current profile data. You may also create new patterns if you discover themes not covered by existing ones."""

        user_message = f"""Please analyze the White Rabbit community and update the community patterns.

First, use the get_community_profile_analysis tool to get full data on all community members including their skills, interests, traits, and profiles. Note: Each member profile includes an "id" field - you MUST use these IDs when saving patterns.
{pattern_context}
Then, for each pattern (existing or new), use the save_pattern tool to persist it.

IMPORTANT: When calling save_pattern, you MUST include related_member_ids as an array of the numeric member IDs (from the "id" field in member_profiles) for members who exhibit the pattern. Be INCLUSIVE - include all members who reasonably fit the pattern, not just the most obvious examples.

Focus on patterns that are:
- Actionable (could lead to introductions or events)
- Non-obvious (go beyond simple frequency counts)
- Community-building (strengthen member connections)

After saving all patterns, summarize what you updated or discovered."""

        return await self._execute_with_tools(user_message)

    async def _execute_with_tools(self, user_message: str) -> dict[str, Any]:
        """Execute a conversation with tool use."""
        tools = [GET_COMMUNITY_ANALYSIS_TOOL, SAVE_PATTERN_TOOL]
        messages = [{"role": "user", "content": user_message}]

        result = {
            "success": False,
            "patterns_found": 0,
            "patterns": [],
            "response_text": "",
        }

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        # Handle tool use in a loop
        while response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_result = await self._execute_tool(block.name, block.input, result)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(tool_result),
                    })

            # Continue conversation with tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

        # Extract final response text
        for block in response.content:
            if hasattr(block, "text"):
                result["response_text"] = block.text
                break

        result["success"] = result["patterns_found"] > 0
        return result

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        result: dict
    ) -> dict:
        """Execute a tool and return the result."""

        if tool_name == "get_community_profile_analysis":
            analysis = await get_community_profile_analysis(self.db)
            return analysis

        elif tool_name == "save_pattern":
            save_result = await save_pattern(self.db, tool_input)
            if "error" not in save_result:
                result["patterns_found"] += 1
                result["patterns"].append({
                    "id": save_result["id"],
                    "name": save_result["name"],
                    "created": save_result["created"],
                })
            return save_result

        return {"error": f"Unknown tool: {tool_name}"}
