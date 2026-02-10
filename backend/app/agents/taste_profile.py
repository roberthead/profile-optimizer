"""LLM-backed agent for building and evolving member taste profiles."""

import json
import logging
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import anthropic

from app.core.config import settings
from app.tools.taste_tools import (
    get_conversation_history,
    get_question_responses,
    get_event_signals,
    get_current_taste_profile,
    update_taste_profile,
    GET_CONVERSATION_HISTORY_TOOL,
    GET_QUESTION_RESPONSES_TOOL,
    GET_EVENT_SIGNALS_TOOL,
    GET_CURRENT_TASTE_PROFILE_TOOL,
    UPDATE_TASTE_PROFILE_TOOL,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a taste profile analyst for White Rabbit Ashland and the Rova events platform.

Your job is to understand members' preferences for events and experiences by analyzing their conversations, question responses, and event behavior. You build evolving taste profiles that help recommend better events.

## What You're Looking For

### Vibe Words (positive resonance)
Words and phrases that indicate what they're drawn to:
- "cozy", "intimate", "weird", "experimental", "low-key"
- "energetic", "vibrant", "creative", "artsy", "chill"
- "outdoor", "community", "handmade", "local", "underground"

### Avoid Words (negative resonance)
Words and phrases that indicate what repels them:
- "crowded", "loud", "mainstream", "corporate", "touristy"
- "high-energy", "formal", "networking", "scene-y"
- "expensive", "stuffy", "pretentious"

### Energy & Time Preferences
- Morning person vs night owl
- High-energy activities vs low-key hangouts
- Solo explorer vs group experiences

### Dealbreakers (hard nos)
- "standing room only" -> dealbreakers: ["standing room"]
- "I hate when there's no parking" -> dealbreakers: ["no parking"]
- "cash only is a pain" -> dealbreakers: ["cash only"]
- "I can't do downtown" -> venue_affinities: {"downtown": -100}

### Anti-Preferences (soft avoids - things they just don't get)
- "I've never understood karaoke" -> not_my_thing: ["karaoke"]
- "Wine tastings aren't really my scene" -> not_my_thing: ["wine tastings"]
- "I don't get the appeal of open mics" -> not_my_thing: ["open mics"]

### Contextual State (temporary conditions)
- "I'm exhausted this week" -> this_week_energy: "low"
- "My friend is visiting from Portland" -> visitors_in_town: true
- "I'm feeling adventurous lately" -> current_mood: "adventurous"
- "Just need some quiet time" -> current_mood: "low-key"

## Detection Examples

From conversations:
- "That sounds exhausting" -> avoid_words: ["high-energy", "exhausting"]
- "I love weird stuff" -> vibe_words: ["weird", "experimental", "unusual"]
- "I never go downtown anymore" -> venue_affinities: {"downtown": -50}
- "The Varsity is my favorite spot" -> venue_affinities: {"Varsity Theatre": 80}
- "I usually go to things alone" -> usual_company: "solo"
- "Only if my partner wants to go" -> usual_company: "duo"

From event signals:
- Consistently attends evening events -> energy_time: "evening"
- RSVPs but often skips free events -> spontaneity: 70 (waits until last minute)
- Always attends Live Music events -> category_affinities: {"Live Music": 80}
- Never clicks on Workshop events -> category_affinities: {"Workshops": -30}

## Updating Profiles

When updating a taste profile:
1. MERGE new insights with existing data, don't overwrite
2. For arrays (vibe_words, avoid_words, etc.): combine old and new, removing duplicates
3. For affinities: adjust scores based on new signals, don't reset
4. For contextual state: this CAN overwrite since it's temporary

## Important Principles

- Extract preferences from HOW they talk, not just WHAT they say
- Anti-preferences are valuable - knowing what someone doesn't like is as useful as what they do like
- Contextual state expires - note when it was set
- Behavior > stated preferences when they conflict
- Be specific: "cozy coffee shop vibes" is better than just "relaxed"
"""


class TasteProfileAgent:
    """LLM-backed agent that builds and evolves member taste profiles."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def analyze_member(self, member_id: int) -> dict[str, Any]:
        """
        Perform a full analysis of a member from all available sources.

        Analyzes conversation history, question responses, and event signals
        to build or update a comprehensive taste profile.

        Args:
            member_id: The member's database ID.

        Returns:
            Dict with analysis results, extracted preferences, and updated profile.
        """
        user_message = f"""Please analyze member {member_id} and build/update their taste profile.

1. First, use get_current_taste_profile to see their existing preferences (if any).

2. Then gather data from all sources:
   - get_conversation_history: Analyze how they talk about events/experiences
   - get_question_responses: Look at their answers for preference signals
   - get_event_signals: Examine their actual behavior (most reliable signal)

3. Analyze all data to extract:
   - Vibe words they resonate with
   - Avoid words that repel them
   - Energy/time preferences
   - Company preferences (solo/duo/group)
   - Dealbreakers (hard nos)
   - Not-my-thing items (soft avoids)
   - Category/venue/organizer affinities from behavior
   - Any contextual state signals

4. Use update_taste_profile to save the merged profile.
   - MERGE with existing data, don't overwrite
   - For arrays: combine and deduplicate
   - For affinities: adjust scores, don't reset

5. Provide a summary of what you learned and what changed.

Focus on being SPECIFIC. "evening person who likes intimate acoustic shows" is much better than "likes music"."""

        return await self._execute_with_tools(user_message, "full_analysis")

    async def update_from_conversation(
        self,
        member_id: int,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        """
        Quick update from new conversation messages.

        Analyzes recent messages for preference signals without a full profile rebuild.
        Optimized for real-time updates during chat sessions.

        Args:
            member_id: The member's database ID.
            messages: List of message dicts with 'role' and 'content' keys.

        Returns:
            Dict with extracted signals and any profile updates made.
        """
        # Format messages for the prompt
        formatted_messages = "\n".join([
            f"[{msg.get('role', 'unknown')}]: {msg.get('content', '')}"
            for msg in messages
        ])

        user_message = f"""Analyze these recent messages from member {member_id} for taste profile signals:

---
{formatted_messages}
---

1. First, get their current taste profile with get_current_taste_profile.

2. Scan the messages for:
   - Vibe words (positive resonance): words that indicate what they're drawn to
   - Avoid words (negative resonance): words that indicate what repels them
   - Energy signals: "exhausting", "energizing", "low-key", etc.
   - Company preferences: mentions of going alone vs with others
   - Dealbreakers: hard nos like "I can't do X"
   - Anti-preferences: "I don't get X", "X isn't my thing"
   - Contextual state: temporary conditions like being tired, having visitors, mood

3. If you find any new signals, use update_taste_profile to merge them with existing data.
   - ONLY update if you found clear signals
   - MERGE, don't overwrite (combine arrays, adjust scores)

4. Return a summary of what signals you detected and what (if anything) you updated.

Be conservative - only extract clear signals, not weak implications."""

        return await self._execute_with_tools(user_message, "conversation_update")

    async def update_context(
        self,
        member_id: int,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update temporary contextual state for a member.

        Used for explicit context updates like "I'm tired this week" or
        "My friend is visiting." These are temporary states that affect
        recommendations but don't represent long-term preferences.

        Args:
            member_id: The member's database ID.
            context: Dict with contextual fields to update. Supported fields:
                - current_mood: str (e.g., "adventurous", "low-key")
                - this_week_energy: "low" | "medium" | "high"
                - visitors_in_town: bool

        Returns:
            Dict with update result.
        """
        # Validate context fields
        valid_fields = {"current_mood", "this_week_energy", "visitors_in_town"}
        filtered_context = {k: v for k, v in context.items() if k in valid_fields}

        if not filtered_context:
            return {
                "success": False,
                "error": f"No valid context fields provided. Valid fields: {valid_fields}",
            }

        # Validate this_week_energy value if provided
        if "this_week_energy" in filtered_context:
            if filtered_context["this_week_energy"] not in ("low", "medium", "high"):
                return {
                    "success": False,
                    "error": "this_week_energy must be 'low', 'medium', or 'high'",
                }

        # Direct update without LLM - this is a simple state change
        result = await update_taste_profile(
            self.db,
            member_id,
            filtered_context,
        )

        if result.get("success"):
            return {
                "success": True,
                "member_id": member_id,
                "updated_context": filtered_context,
                "message": "Contextual state updated successfully.",
            }
        else:
            return result

    async def _execute_with_tools(
        self,
        user_message: str,
        operation_type: str,
    ) -> dict[str, Any]:
        """Execute a conversation with tool use."""
        tools = [
            GET_CONVERSATION_HISTORY_TOOL,
            GET_QUESTION_RESPONSES_TOOL,
            GET_EVENT_SIGNALS_TOOL,
            GET_CURRENT_TASTE_PROFILE_TOOL,
            UPDATE_TASTE_PROFILE_TOOL,
        ]

        messages = [{"role": "user", "content": user_message}]

        result: dict[str, Any] = {
            "success": False,
            "operation": operation_type,
            "signals_detected": [],
            "profile_updated": False,
            "response_text": "",
        }

        try:
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
                        tool_result = await self._execute_tool(
                            block.name,
                            block.input,
                            result,
                        )
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

            result["success"] = True

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error in TasteProfileAgent: {e}")
            result["error"] = f"API error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in TasteProfileAgent: {e}")
            result["error"] = f"Unexpected error: {str(e)}"

        return result

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        result: dict,
    ) -> dict[str, Any]:
        """Execute a tool and return the result."""

        try:
            if tool_name == "get_conversation_history":
                return await get_conversation_history(
                    self.db,
                    tool_input["member_id"],
                    limit=tool_input.get("limit", 50),
                    session_id=tool_input.get("session_id"),
                )

            elif tool_name == "get_question_responses":
                return await get_question_responses(
                    self.db,
                    tool_input["member_id"],
                    limit=tool_input.get("limit", 100),
                )

            elif tool_name == "get_event_signals":
                return await get_event_signals(
                    self.db,
                    tool_input["member_id"],
                    days_back=tool_input.get("days_back", 90),
                )

            elif tool_name == "get_current_taste_profile":
                return await get_current_taste_profile(
                    self.db,
                    tool_input["member_id"],
                )

            elif tool_name == "update_taste_profile":
                update_result = await update_taste_profile(
                    self.db,
                    tool_input["member_id"],
                    tool_input.get("updates", {}),
                )

                if update_result.get("success"):
                    result["profile_updated"] = True
                    result["signals_detected"].extend(
                        update_result.get("updated_fields", [])
                    )

                return update_result

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": f"Tool execution error: {str(e)}"}
