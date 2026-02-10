"""LLM-backed agent for discovering edges (connections) between community members."""

import json
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
import anthropic

from app.core.config import settings
from app.tools.graph_tools import (
    get_all_members_with_profiles,
    get_existing_edges,
    get_active_patterns,
    save_edge,
    GET_ALL_MEMBERS_TOOL,
    GET_EXISTING_EDGES_TOOL,
    GET_ACTIVE_PATTERNS_TOOL,
    SAVE_EDGE_TOOL,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a community connection analyst for White Rabbit Ashland, a creative community focused on technology, entrepreneurship, and the arts.

Your task is to discover meaningful connections between members by analyzing their profiles. These connections (edges) form a social graph that powers introductions, event matching, and collaboration suggestions.

## Edge Types You Can Create

1. **shared_skill** - Both members have the same skill(s)
   - Look for exact matches AND semantic similarities (e.g., "Python" and "programming")
   - Strength based on number and specificity of shared skills

2. **shared_interest** - Both members share an interest
   - Can be exact matches or closely related topics
   - Consider that interests like "AI" and "machine learning" are related

3. **collaboration_potential** - Complementary skills that could work well together
   - This is the MOST VALUABLE type - non-obvious connections
   - Example: A designer + a developer, a writer + a photographer
   - Look for skills that CREATE when combined

4. **pattern_connection** - Both members belong to a discovered community pattern
   - Use the patterns from get_active_patterns as evidence
   - This shows meta-level community structure

## Quality Over Quantity

Focus on discovering MEANINGFUL connections, not exhaustively listing every possible pair:

- **Strong connections (strength 80-100):** 3+ shared skills/interests OR deep complementary fit
- **Moderate connections (strength 60-79):** 2 shared items OR good collaboration potential
- **Light connections (strength 50-59):** 1 meaningful shared item
- **Skip connections below 50** - they add noise, not signal

## What Makes a Connection Non-Obvious

The best edges are ones that:
- Cross domain boundaries (arts + technology, entrepreneurship + community building)
- Reveal unexpected complementarity (a "storyteller" and a "data scientist" both deal with narratives)
- Connect people who might not realize they have common ground
- Could spark a real conversation or collaboration

## Evidence Requirements

Every edge MUST have evidence explaining WHY the connection exists:
- List the specific shared skills/interests
- For collaboration_potential, explain what each person brings
- For pattern_connection, reference the pattern name and ID
- Include a brief "notes" field explaining why this matters

## Analysis Approach

1. First, get all members and existing edges to understand the current state
2. Get active patterns to use as additional connection evidence
3. For each member pair, analyze:
   - Skill overlap (exact and semantic)
   - Interest overlap (exact and semantic)
   - Complementary abilities (what could they build together?)
   - Pattern co-membership
4. Only create edges for meaningful connections (strength >= 50)
5. Prioritize non-obvious, cross-domain connections

## Semantic Matching Tips

Look beyond exact keyword matches:
- "writing" and "copywriting" and "content creation" are related
- "leadership" and "team building" and "management" overlap
- "photography" and "visual arts" and "design" connect
- "entrepreneurship" and "startups" and "business development" align
- "AI" and "machine learning" and "deep learning" are connected

Remember: You're not just matching keywords - you're finding the hidden social fabric of a creative community."""


class EdgeDiscoveryAgent:
    """LLM-backed agent that discovers connections between community members."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def discover_edges(self) -> dict[str, Any]:
        """
        Analyze all member pairs and discover meaningful connections.

        Returns:
            Dict with edges_created count, edges_updated count, edge details, and response text.
        """
        logger.info("Starting edge discovery process")

        user_message = """Please analyze the White Rabbit community and discover meaningful connections between members.

Follow these steps:

1. First, use get_all_members_with_profiles to get all member data (skills, interests, bios, etc.)

2. Then use get_existing_edges to see what connections already exist (to avoid duplicates)

3. Use get_active_patterns to get community patterns that can serve as edge evidence

4. Analyze member pairs for meaningful connections. Focus on:
   - Shared skills (exact and semantic matches)
   - Shared interests (exact and semantic matches)
   - Collaboration potential (complementary skills that could create together)
   - Pattern connections (members in the same discovered patterns)

5. For each meaningful connection (strength >= 50), use save_edge to create it

IMPORTANT Guidelines:
- Quality over quantity - focus on the most meaningful connections
- Include proper evidence for each edge (shared_skills, shared_interests, notes, etc.)
- Prioritize non-obvious, cross-domain connections
- Don't create edges between every pair - only where there's real signal
- Check existing_edges to avoid duplicates

After creating edges, provide a summary of:
- How many edges were created
- The strongest/most interesting connections found
- Any patterns you noticed in the community graph"""

        return await self._execute_with_tools(user_message)

    async def discover_edges_for_member(self, member_id: int) -> dict[str, Any]:
        """
        Discover edges for a specific member.

        Useful when a member's profile is updated and we want to find new connections.

        Args:
            member_id: The ID of the member to find connections for.

        Returns:
            Dict with edges found for this specific member.
        """
        logger.info(f"Starting edge discovery for member {member_id}")

        user_message = f"""Please discover connections for member ID {member_id}.

Follow these steps:

1. Use get_all_members_with_profiles to get all member data

2. Use get_existing_edges to see what connections already exist for this member

3. Use get_active_patterns to get patterns this member might be part of

4. Find all meaningful connections between member {member_id} and other members:
   - Look at their skills and find others with matching or complementary skills
   - Look at their interests and find others with shared interests
   - Check if they share any patterns with other members
   - Consider collaboration potential based on complementary abilities

5. For each meaningful connection (strength >= 50), use save_edge to create it

Focus on quality - only create edges where there's a real connection that could lead to a valuable introduction or collaboration.

After creating edges, summarize the connections found for this member."""

        return await self._execute_with_tools(user_message)

    async def refresh_pattern_edges(self) -> dict[str, Any]:
        """
        Create edges based on pattern membership.

        Members who share the same pattern should have pattern_connection edges.

        Returns:
            Dict with pattern-based edges created.
        """
        logger.info("Starting pattern-based edge discovery")

        user_message = """Please create edges between members who share the same community patterns.

Follow these steps:

1. Use get_active_patterns to get all patterns with their related_member_ids

2. Use get_existing_edges to check for existing pattern_connection edges

3. For each pattern that has 2+ members:
   - Create pattern_connection edges between members in that pattern
   - Use the pattern name and ID as evidence
   - Strength should be based on how strong the pattern membership is

4. Use save_edge for each new pattern connection

Focus on patterns that are most meaningful for community connection - skip trivial patterns.

Summarize how many pattern-based connections were created and which patterns generated the most edges."""

        return await self._execute_with_tools(user_message)

    async def _execute_with_tools(self, user_message: str) -> dict[str, Any]:
        """Execute a conversation with tool use."""
        tools = [
            GET_ALL_MEMBERS_TOOL,
            GET_EXISTING_EDGES_TOOL,
            GET_ACTIVE_PATTERNS_TOOL,
            SAVE_EDGE_TOOL,
        ]
        messages = [{"role": "user", "content": user_message}]

        result = {
            "success": False,
            "edges_created": 0,
            "edges_updated": 0,
            "edges_skipped": 0,
            "edges": [],
            "response_text": "",
            "errors": [],
        }

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,  # Higher limit for graph analysis
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            result["errors"].append(f"API error: {str(e)}")
            return result

        # Handle tool use in a loop
        iteration_count = 0
        max_iterations = 50  # Safety limit

        while response.stop_reason == "tool_use" and iteration_count < max_iterations:
            iteration_count += 1
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    logger.debug(f"Executing tool: {block.name}")
                    try:
                        tool_result = await self._execute_tool(block.name, block.input, result)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(tool_result),
                        })
                    except Exception as e:
                        logger.error(f"Tool execution error for {block.name}: {e}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"error": str(e)}),
                            "is_error": True,
                        })
                        result["errors"].append(f"Tool {block.name} error: {str(e)}")

            # Continue conversation with tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    system=SYSTEM_PROMPT,
                    tools=tools,
                    messages=messages,
                )
            except anthropic.APIError as e:
                logger.error(f"Anthropic API error in tool loop: {e}")
                result["errors"].append(f"API error: {str(e)}")
                break

        if iteration_count >= max_iterations:
            logger.warning(f"Hit max iteration limit ({max_iterations}) in edge discovery")
            result["errors"].append(f"Hit iteration limit of {max_iterations}")

        # Extract final response text
        for block in response.content:
            if hasattr(block, "text"):
                result["response_text"] = block.text
                break

        result["success"] = result["edges_created"] > 0 or result["edges_updated"] > 0
        logger.info(
            f"Edge discovery complete: {result['edges_created']} created, "
            f"{result['edges_updated']} updated, {result['edges_skipped']} skipped"
        )

        return result

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        result: dict
    ) -> dict:
        """Execute a tool and return the result."""

        if tool_name == "get_all_members_with_profiles":
            members_data = await get_all_members_with_profiles(self.db)
            logger.info(f"Fetched {members_data['total_members']} members for analysis")
            return members_data

        elif tool_name == "get_existing_edges":
            edges_data = await get_existing_edges(self.db)
            logger.info(f"Found {edges_data['total_edges']} existing edges")
            return edges_data

        elif tool_name == "get_active_patterns":
            patterns_data = await get_active_patterns(self.db)
            logger.info(f"Found {patterns_data['total_patterns']} active patterns")
            return patterns_data

        elif tool_name == "save_edge":
            save_result = await save_edge(self.db, tool_input)

            if "error" in save_result:
                logger.warning(f"Edge save error: {save_result['error']}")
                return save_result

            status = save_result.get("status")
            if status == "created":
                result["edges_created"] += 1
                result["edges"].append({
                    "id": save_result["id"],
                    "member_a_id": save_result["member_a_id"],
                    "member_b_id": save_result["member_b_id"],
                    "edge_type": save_result["edge_type"],
                    "strength": save_result["strength"],
                    "status": "created",
                })
            elif status == "updated":
                result["edges_updated"] += 1
                result["edges"].append({
                    "id": save_result["id"],
                    "strength": save_result["strength"],
                    "status": "updated",
                })
            elif status == "already_exists":
                result["edges_skipped"] += 1

            return save_result

        logger.warning(f"Unknown tool requested: {tool_name}")
        return {"error": f"Unknown tool: {tool_name}"}
