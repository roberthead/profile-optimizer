"""LLM-backed agent for selecting questions tailored to group contexts."""

import json
import logging
from typing import Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import anthropic

from app.core.config import settings
from app.models import Question, QuestionVibe
from app.tools.group_tools import (
    get_present_member_profiles,
    get_group_edges,
    get_recent_group_questions,
    score_question_for_group,
    GET_PRESENT_MEMBER_PROFILES_TOOL,
    GET_GROUP_EDGES_TOOL,
    GET_RECENT_GROUP_QUESTIONS_TOOL,
    SCORE_QUESTION_FOR_GROUP_TOOL,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a group facilitator agent for White Rabbit Ashland, a creative community focused on technology, entrepreneurship, and the arts.

Your job is to select the PERFECT question for a group of community members who are together. Unlike individual question targeting, group questions should:

1. **Connect Multiple People** - The best questions involve or interest several people in the room
2. **Leverage Existing Relationships** - Use the edges/connections between present members
3. **Match the Group Energy** - Consider time of day, meeting context, and collective vibe
4. **Spark Conversation** - Questions should open dialogue, not close it
5. **Stay Fresh** - Avoid recently asked questions

## Understanding the Group

When analyzing a group, look for:
- **Shared Skills/Interests**: What do multiple members have in common?
- **Complementary Skills**: What interesting combinations exist?
- **Strong Edges**: Which relationships are already well-developed?
- **Pattern Overlap**: Are members part of the same community patterns?
- **Collective Vibe**: What's the dominant energy level and preference?

## Time of Day Considerations

- **Morning**: Energizing, lighter questions work well. Save deep questions for later.
- **Afternoon**: Balanced energy. Good for connector and collaboration questions.
- **Evening**: Can go deeper. Playful and provocative questions work well.
- **Late Night**: Intimate, weird, or philosophical questions shine.

## Meeting Context Types

- **casual**: Prioritize playful, connector, or warm vibes
- **workshop**: Can handle deep or challenging questions
- **social**: Fun, icebreaker-style questions
- **retreat**: Great for deep, introspective questions
- **demo_day**: Questions about work, collaboration potential
- **first_meeting**: Warm, accessible questions that help people connect

## Scoring Criteria

When evaluating questions for a group:

1. **Multi-Member Relevance (0-30 points)**
   - Does the question relate to multiple present members?
   - Is it about shared patterns or interests?

2. **Edge Utilization (0-25 points)**
   - Does it involve connections between present members?
   - Could it strengthen existing weak ties?

3. **Group Vibe Match (0-25 points)**
   - Does the question vibe match the group's collective taste?
   - Is it appropriate for the meeting context?

4. **Discussion Potential (0-10 points)**
   - Would this spark interesting group conversation?
   - Is it accessible enough that everyone can contribute?

5. **Time Appropriateness (0-10 points)**
   - Is it right for the time of day?
   - Is the difficulty level appropriate?

## Selection Strategy

After scoring, apply NON-DETERMINISTIC selection:
- 70% chance: Select the highest-scoring question
- 20% chance: Random from top 5 (adds variety)
- 10% chance: Wildcard selection (serendipity)

This ensures we don't always pick the same "optimal" question for similar groups.

## Output Requirements

Always return:
- **question_id**: The selected question's database ID
- **targeting_reason**: 2-3 sentences explaining why this question for this group
- **suggested_for_members**: List of member IDs who should be specifically invited to answer
- **vibe_match**: Boolean indicating if the question vibe aligns with group taste"""


class GroupQuestionAgent:
    """LLM-backed agent that selects questions tailored to group contexts."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def select_group_question(
        self,
        context: dict,
        present_member_ids: List[int],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Select the best question for a group of present members.

        Analyzes profiles, edges, and context to find questions that:
        - Connect multiple present members
        - Leverage existing relationships
        - Match the group's collective vibe
        - Are appropriate for the time and meeting type

        Args:
            context: Dict with group context including:
                - time_of_day: "morning" | "afternoon" | "evening" | "night"
                - meeting_type: "casual" | "workshop" | "social" | "retreat" | etc.
                - additional context as needed
            present_member_ids: List of member IDs who are present
            db: Database session (used by internal tools)

        Returns:
            Dict containing:
                - question_id: Selected question ID
                - targeting_reason: Why this question for this group
                - suggested_for_members: Member IDs to involve
                - vibe_match: Whether vibe aligned with group
                - score: The question's group fit score
                - selection_method: How the question was selected
        """
        if not present_member_ids:
            return {
                "error": "No present member IDs provided",
                "question_id": None,
            }

        if len(present_member_ids) < 2:
            return {
                "error": "Need at least 2 members for group question selection",
                "question_id": None,
            }

        logger.info(
            f"Selecting group question for {len(present_member_ids)} members, "
            f"context: {context.get('meeting_type', 'unknown')} at {context.get('time_of_day', 'unknown')}"
        )

        # Format context for the prompt
        context_str = json.dumps(context, indent=2)

        user_message = f"""Please select the best question for this group gathering.

## Group Context
{context_str}

## Present Member IDs
{present_member_ids}

## Your Task

1. First, gather information about the group:
   - Use get_present_member_profiles to understand who is present
   - Use get_group_edges to see existing connections between them
   - Use get_recent_group_questions to find questions to avoid

2. Analyze the group:
   - What skills/interests do they share?
   - What patterns are they part of?
   - What's the collective vibe (based on taste profiles)?
   - How well-connected is the group (edge density)?

3. Get available questions and score them:
   - For each promising question, use score_question_for_group
   - Consider how well it fits this specific group and context
   - Factor in time of day: {context.get('time_of_day', 'afternoon')}
   - Factor in meeting type: {context.get('meeting_type', 'casual')}

4. Apply selection algorithm:
   - 70% chance: Pick highest scoring question
   - 20% chance: Random from top 5
   - 10% chance: Wildcard for serendipity

5. Return your selection with:
   - question_id
   - targeting_reason (2-3 sentences explaining the choice)
   - suggested_for_members (who should be invited to answer first)
   - vibe_match (true/false)

Focus on finding a question that will spark meaningful group conversation and connection."""

        return await self._execute_with_tools(user_message, present_member_ids)

    async def _get_question_candidates(
        self,
        exclude_ids: List[int],
        limit: int = 50,
    ) -> List[dict[str, Any]]:
        """Get candidate questions for group selection."""
        query = select(Question).where(Question.is_active == True)

        if exclude_ids:
            query = query.where(Question.id.notin_(exclude_ids))

        query = query.order_by(Question.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        questions = result.scalars().all()

        return [
            {
                "id": q.id,
                "question_id": str(q.question_id),
                "question_text": q.question_text,
                "category": q.category.value,
                "question_type": q.question_type.value,
                "difficulty_level": q.difficulty_level,
                "vibe": q.vibe.value if q.vibe else None,
                "relevant_member_ids": q.relevant_member_ids or [],
                "edge_context": q.edge_context or {},
                "targeting_criteria": q.targeting_criteria or {},
            }
            for q in questions
        ]

    async def _execute_with_tools(
        self,
        user_message: str,
        present_member_ids: List[int],
    ) -> dict[str, Any]:
        """Execute conversation with tool use."""
        # Define tools - we'll also add a tool to get questions
        get_questions_tool = {
            "name": "get_question_candidates",
            "description": """Get candidate questions for group selection.

Returns a list of active questions with their targeting metadata.
Excludes recently asked questions if provided.

Use this to get the pool of questions to score and select from.""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "exclude_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Question IDs to exclude (e.g., recently asked)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum questions to return (default: 50)"
                    }
                },
                "required": []
            }
        }

        tools = [
            GET_PRESENT_MEMBER_PROFILES_TOOL,
            GET_GROUP_EDGES_TOOL,
            GET_RECENT_GROUP_QUESTIONS_TOOL,
            SCORE_QUESTION_FOR_GROUP_TOOL,
            get_questions_tool,
        ]

        messages = [{"role": "user", "content": user_message}]

        result: dict[str, Any] = {
            "success": False,
            "question_id": None,
            "targeting_reason": "",
            "suggested_for_members": [],
            "vibe_match": False,
            "score": 0,
            "selection_method": "",
            "response_text": "",
        }

        # Store data for scoring
        cached_profiles: Optional[List[dict]] = None
        cached_edges: Optional[List[dict]] = None

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

            # Handle tool use in a loop
            iteration = 0
            max_iterations = 30

            while response.stop_reason == "tool_use" and iteration < max_iterations:
                iteration += 1
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        logger.debug(f"Executing tool: {block.name}")
                        try:
                            tool_result = await self._execute_tool(
                                block.name,
                                block.input,
                                present_member_ids,
                                cached_profiles,
                                cached_edges,
                            )

                            # Cache profiles and edges for scoring
                            if block.name == "get_present_member_profiles":
                                cached_profiles = tool_result
                            elif block.name == "get_group_edges":
                                cached_edges = tool_result

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

            if iteration >= max_iterations:
                logger.warning("Group question agent reached max iterations")
                result["error"] = "Reached maximum iterations"

            # Extract final response and parse it
            for block in response.content:
                if hasattr(block, "text"):
                    result["response_text"] = block.text
                    # Try to extract structured data from the response
                    self._parse_response(block.text, result)
                    break

            result["success"] = result["question_id"] is not None

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error in GroupQuestionAgent: {e}")
            result["error"] = f"API error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in GroupQuestionAgent: {e}")
            result["error"] = f"Unexpected error: {str(e)}"

        return result

    def _parse_response(self, text: str, result: dict) -> None:
        """Parse the LLM response to extract structured data."""
        import re

        # Try to find question_id
        id_match = re.search(r'question_id["\s:]+(\d+)', text, re.IGNORECASE)
        if id_match:
            result["question_id"] = int(id_match.group(1))

        # Try to find targeting_reason
        reason_match = re.search(
            r'targeting_reason["\s:]+["\']?([^"\']+)["\']?',
            text,
            re.IGNORECASE
        )
        if reason_match:
            result["targeting_reason"] = reason_match.group(1).strip()

        # Try to find vibe_match
        vibe_match = re.search(r'vibe_match["\s:]+(\w+)', text, re.IGNORECASE)
        if vibe_match:
            result["vibe_match"] = vibe_match.group(1).lower() in ("true", "yes", "1")

        # Try to find suggested_for_members
        members_match = re.search(
            r'suggested_for_members["\s:]+\[([^\]]+)\]',
            text,
            re.IGNORECASE
        )
        if members_match:
            try:
                member_ids = [
                    int(x.strip())
                    for x in members_match.group(1).split(",")
                    if x.strip().isdigit()
                ]
                result["suggested_for_members"] = member_ids
            except ValueError:
                pass

        # Try to find score
        score_match = re.search(r'score["\s:]+(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        if score_match:
            result["score"] = float(score_match.group(1))

        # Try to find selection_method
        method_match = re.search(
            r'selection_method["\s:]+["\']?(\w+)["\']?',
            text,
            re.IGNORECASE
        )
        if method_match:
            result["selection_method"] = method_match.group(1)

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        present_member_ids: List[int],
        cached_profiles: Optional[List[dict]],
        cached_edges: Optional[List[dict]],
    ) -> Any:
        """Execute a tool and return the result."""

        if tool_name == "get_present_member_profiles":
            member_ids = tool_input.get("member_ids", present_member_ids)
            profiles = await get_present_member_profiles(self.db, member_ids)
            return profiles

        elif tool_name == "get_group_edges":
            member_ids = tool_input.get("member_ids", present_member_ids)
            edges = await get_group_edges(self.db, member_ids)
            return edges

        elif tool_name == "get_recent_group_questions":
            member_ids = tool_input.get("member_ids", present_member_ids)
            days = tool_input.get("days", 7)
            question_ids = await get_recent_group_questions(self.db, member_ids, days)
            return {"recent_question_ids": question_ids, "count": len(question_ids)}

        elif tool_name == "get_question_candidates":
            exclude_ids = tool_input.get("exclude_ids", [])
            limit = tool_input.get("limit", 50)
            questions = await self._get_question_candidates(exclude_ids, limit)
            return {"questions": questions, "count": len(questions)}

        elif tool_name == "score_question_for_group":
            question = tool_input.get("question", {})
            members = tool_input.get("members", cached_profiles or [])
            edges = tool_input.get("edges", cached_edges or [])

            score = score_question_for_group(question, members, edges)
            return {"score": score, "question_id": question.get("id")}

        return {"error": f"Unknown tool: {tool_name}"}
