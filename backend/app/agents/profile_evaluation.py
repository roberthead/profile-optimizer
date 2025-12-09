"""LLM-backed agent for evaluating member profile health."""

import json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import anthropic

from app.models import Member, ProfileCompleteness
from app.core.config import settings
from app.tools.profile_tools import get_field_completeness, FIELD_COMPLETENESS_TOOL


SYSTEM_PROMPT = """You are a profile health evaluator for the White Rabbit Ashland community - a creative community focused on technology, entrepreneurship, and the arts.

Your job is to assess member profiles and provide:
1. A completeness score (0-100)
2. Specific, actionable recommendations for improvement
3. Quality assessment of existing content

When evaluating profiles, consider:
- **Discoverability**: Can other community members find this person for collaboration? Skills, interests, and a clear bio are crucial.
- **Professional context**: Role, company, and website help establish credibility.
- **Community connection**: What makes this person unique? What do they bring to the community?
- **Quality over quantity**: A thoughtful bio is better than a generic one. Specific skills are better than vague ones.

Scoring guidelines:
- 0-30%: Minimal profile - just basic identity info
- 31-50%: Partial profile - some info but missing key elements for discovery
- 51-70%: Good profile - has core elements but could be richer
- 71-85%: Strong profile - well-rounded with good discoverability
- 86-100%: Excellent profile - comprehensive, specific, and community-ready

Be encouraging but honest. The goal is to help members build profiles that enable meaningful community connections."""


class ProfileEvaluationAgent:
    """LLM-backed agent that evaluates member profile completeness and quality."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def evaluate_profile(self, member_id: int) -> dict[str, Any]:
        """
        Evaluate a member's profile using Claude with tool use.

        Returns:
            Dict with completeness_score, quality_assessment, recommendations, field_status
        """
        # First, get the member to pass to the tool
        result = await self.db.execute(select(Member).where(Member.id == member_id))
        member = result.scalar_one_or_none()

        if not member:
            raise ValueError(f"Member with id {member_id} not found")

        # Get field completeness data (we'll provide this to the agent)
        field_data = get_field_completeness(member)

        # Build the prompt
        user_message = f"""Please evaluate the profile health for member: {field_data['member_name']}

First, use the get_field_completeness tool to check the current state of their profile fields, then provide your assessment."""

        # Call Claude with tools
        messages = [{"role": "user", "content": user_message}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[FIELD_COMPLETENESS_TOOL],
            messages=messages,
        )

        # Handle tool use
        while response.stop_reason == "tool_use":
            # Find the tool use block
            tool_use_block = next(
                (block for block in response.content if block.type == "tool_use"),
                None
            )

            if tool_use_block and tool_use_block.name == "get_field_completeness":
                # Execute the tool with our pre-fetched member
                tool_result = field_data

                # Continue the conversation with the tool result
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": json.dumps(tool_result),
                    }]
                })

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    tools=[FIELD_COMPLETENESS_TOOL],
                    messages=messages,
                )
            else:
                break

        # Extract the final text response
        assessment_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                assessment_text = block.text
                break

        # Parse the assessment to extract structured data
        evaluation_result = self._parse_assessment(assessment_text, field_data)

        # Store the result
        await self._store_result(member_id, evaluation_result)

        return evaluation_result

    def _parse_assessment(self, assessment_text: str, field_data: dict) -> dict[str, Any]:
        """Parse the LLM's assessment into structured data."""
        # Try to extract a score from the text
        import re
        score_match = re.search(r'(\d{1,3})%', assessment_text)
        score = int(score_match.group(1)) if score_match else field_data["basic_completeness_percentage"]

        # Ensure score is in valid range
        score = max(0, min(100, score))

        return {
            "completeness_score": score,
            "basic_field_percentage": field_data["basic_completeness_percentage"],
            "assessment": assessment_text,
            "filled_fields": field_data["filled_fields"],
            "empty_fields": field_data["empty_fields"],
            "field_details": field_data["field_details"],
        }

    async def _store_result(self, member_id: int, evaluation: dict) -> None:
        """Store the evaluation result in the database."""
        from datetime import datetime

        result = await self.db.execute(
            select(ProfileCompleteness).where(ProfileCompleteness.member_id == member_id)
        )
        profile_completeness = result.scalar_one_or_none()

        missing_fields_data = {
            "required": [f for f in evaluation["empty_fields"] if f in ["First Name", "Last Name", "Email"]],
            "optional": [f for f in evaluation["empty_fields"] if f not in ["First Name", "Last Name", "Email"]],
        }

        if profile_completeness:
            profile_completeness.completeness_score = evaluation["completeness_score"]
            profile_completeness.missing_fields = missing_fields_data
            profile_completeness.assessment = evaluation["assessment"]
            profile_completeness.last_calculated = datetime.utcnow()
        else:
            profile_completeness = ProfileCompleteness(
                member_id=member_id,
                completeness_score=evaluation["completeness_score"],
                missing_fields=missing_fields_data,
                assessment=evaluation["assessment"],
                last_calculated=datetime.utcnow()
            )
            self.db.add(profile_completeness)

        await self.db.commit()
