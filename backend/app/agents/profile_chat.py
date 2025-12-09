"""LLM-backed agent for conversational profile optimization."""

import json
import uuid
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import anthropic

from app.models import Member, ConversationHistory, ProfileSuggestion, ProfileCompleteness
from app.core.config import settings
from app.tools.profile_tools import get_field_completeness, FIELD_COMPLETENESS_TOOL, SAVE_PROFILE_SUGGESTION_TOOL


SYSTEM_PROMPT = """You are a profile assistant for White Rabbit Ashland—a creative community focused on technology, entrepreneurship, and the arts.

Your job is to have natural conversations with members to help them build rich, discoverable profiles. Nothing is published without their explicit approval; you're drafting suggestions for their review.

## Conversation approach

- **Start by understanding context**: Check their current profile to see what's already there and what's missing
- **Be curious, not comprehensive**: Focus on one or two areas per exchange—don't overwhelm
- **Ask short, open questions**: "What kind of work energizes you?" beats "Can you tell me about your professional background, skills, and interests?"
- **Listen for specifics**: When someone says "I do consulting," gently probe: "What kind? Who do you love working with?"
- **Match their energy**: If they're brief, stay brief. If they want to chat, chat.

## When to save suggestions

Use `save_profile_suggestion` when you have enough context to draft something useful—not before. A good suggestion:
- Reflects their actual words and personality
- Is specific enough to be interesting ("product designer specializing in accessibility" not "designer")
- Feels like them, not like marketing copy

Always tell them you've saved a draft and that they can edit or reject it.

## Profile fields

| Field | What makes it good |
|-------|-------------------|
| **bio** | 1-3 sentences capturing who they are. Personality > formality. |
| **role** | Specific title or description of what they do |
| **location** | Where they're based (city or region) |
| **company** | Current organization, or "Independent" / freelance description |
| **website** | Personal site, portfolio, or relevant link |
| **skills** | Concrete abilities—tools, techniques, domains |
| **interests** | What they're curious about, learning, or passionate about |

## Tone

Warm, unhurried, genuinely interested. You're a helpful neighbor, not a form to fill out. If they're hesitant about sharing something, let it go—there's no quota to hit.
"""


class ProfileChatAgent:
    """LLM-backed agent for conversational profile building."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def chat(self, member_id: int, message: str, session_id: Optional[str] = None) -> dict[str, Any]:
        """
        Process a chat message and return the agent's response.

        Args:
            member_id: The member's database ID
            message: The user's message
            session_id: Optional session ID for conversation continuity

        Returns:
            Dict with response text, session_id, and any suggestions made
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        # Get member data
        result = await self.db.execute(select(Member).where(Member.id == member_id))
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError(f"Member with id {member_id} not found")

        # Get conversation history for this session
        history = await self._get_conversation_history(member_id, session_id)

        # Get current profile completeness for context
        field_data = get_field_completeness(member)

        # Build messages for Claude
        messages = self._build_messages(history, message, field_data)

        # Store user message
        await self._save_message(member_id, session_id, "user", message)

        # Call Claude with tools
        tools = [FIELD_COMPLETENESS_TOOL, SAVE_PROFILE_SUGGESTION_TOOL]
        suggestions_made = []

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
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
                        member,
                        member_id,
                        session_id,
                        field_data,
                        suggestions_made
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
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

        # Extract final response text
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text = block.text
                break

        # Store assistant response
        await self._save_message(member_id, session_id, "assistant", response_text)

        return {
            "response": response_text,
            "session_id": session_id,
            "suggestions_made": suggestions_made,
        }

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        member: Member,
        member_id: int,
        session_id: str,
        field_data: dict,
        suggestions_made: list
    ) -> dict:
        """Execute a tool and return the result."""

        if tool_name == "get_field_completeness":
            return field_data

        elif tool_name == "save_profile_suggestion":
            # Get current value for the field
            field_name = tool_input["field_name"]
            current_value = getattr(member, field_name, None)
            if isinstance(current_value, list):
                current_value = ", ".join(current_value) if current_value else None

            # Create suggestion record
            suggestion = ProfileSuggestion(
                member_id=member_id,
                session_id=session_id,
                field_name=field_name,
                current_value=str(current_value) if current_value else None,
                suggested_value=tool_input["suggested_value"],
                reasoning=tool_input.get("reasoning", ""),
                status="pending",
            )
            self.db.add(suggestion)
            await self.db.commit()
            await self.db.refresh(suggestion)

            suggestions_made.append({
                "id": suggestion.id,
                "field_name": field_name,
                "suggested_value": tool_input["suggested_value"],
                "reasoning": tool_input.get("reasoning", ""),
            })

            return {
                "success": True,
                "message": f"Suggestion saved for {field_name}. The member can review and approve it.",
                "suggestion_id": suggestion.id,
            }

        return {"error": f"Unknown tool: {tool_name}"}

    async def _get_conversation_history(self, member_id: int, session_id: str) -> list[dict]:
        """Get conversation history for this session."""
        result = await self.db.execute(
            select(ConversationHistory)
            .where(ConversationHistory.member_id == member_id)
            .where(ConversationHistory.session_id == session_id)
            .order_by(ConversationHistory.created_at)
        )
        messages = result.scalars().all()

        return [
            {"role": msg.role, "content": msg.message_content}
            for msg in messages
        ]

    async def _save_message(self, member_id: int, session_id: str, role: str, content: str) -> None:
        """Save a message to conversation history."""
        message = ConversationHistory(
            member_id=member_id,
            session_id=session_id,
            role=role,
            message_content=content,
        )
        self.db.add(message)
        await self.db.commit()

    def _build_messages(self, history: list[dict], current_message: str, field_data: dict) -> list[dict]:
        """Build the messages array for Claude."""
        messages = []

        # If this is the start of conversation, include context
        if not history:
            context = f"""This is the start of a conversation with {field_data['member_name']}.

Their profile is currently {field_data['basic_completeness_percentage']}% complete.

Filled fields: {', '.join(field_data['filled_fields']) if field_data['filled_fields'] else 'None'}

Empty fields that could be filled: {', '.join(field_data['empty_fields']) if field_data['empty_fields'] else 'All fields are complete!'}

Start by warmly greeting them and asking how you can help with their profile today."""

            messages.append({"role": "user", "content": context})
            messages.append({"role": "assistant", "content": f"Hi {field_data['member_name'].split()[0] if field_data['member_name'] else 'there'}! I'm here to help you build out your White Rabbit profile. I see your profile is about {field_data['basic_completeness_percentage']}% complete - would you like to chat about filling in some of the missing pieces? I'm happy to help with whatever feels most relevant to you."})

        # Add conversation history
        for msg in history:
            messages.append(msg)

        # Add current message
        messages.append({"role": "user", "content": current_message})

        return messages

    async def get_session_history(self, member_id: int, session_id: str) -> list[dict]:
        """Get the full conversation history for a session."""
        return await self._get_conversation_history(member_id, session_id)
