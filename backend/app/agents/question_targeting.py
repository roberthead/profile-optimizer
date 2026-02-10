"""LLM-backed agent for intelligent question targeting to community members."""

import json
import logging
import random
from typing import Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime, timedelta, timezone
import anthropic

from app.models import (
    Member,
    Question,
    QuestionDelivery,
    Pattern,
    DeliveryChannel,
    DeliveryStatus,
    QuestionVibe,
)
from app.core.config import settings
from app.tools.targeting_tools import (
    get_question_pool,
    get_member_context,
    get_member_edges,
    get_answered_questions,
    assign_question_to_member,
    get_all_members_for_targeting,
    GET_QUESTION_POOL_TOOL,
    GET_MEMBER_CONTEXT_TOOL,
    GET_MEMBER_EDGES_TOOL,
    GET_ANSWERED_QUESTIONS_TOOL,
    ASSIGN_QUESTION_TO_MEMBER_TOOL,
    GET_ALL_MEMBERS_FOR_TARGETING_TOOL,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a question targeting agent for White Rabbit Ashland - a creative community focused on technology, entrepreneurship, and the arts.

Your job is to match the RIGHT questions to the RIGHT members at the RIGHT time. You're not just randomly distributing questions - you're creating meaningful moments of discovery and connection.

## Core Philosophy

**Meaningful connections over random selection.** Every question should feel like it was chosen specifically for that person, because it was. When a member receives a question about someone they're connected to, or a topic that matches their vibe, magic happens.

**Respect member energy.** Use taste profiles to understand:
- Their vibe_words tell you what resonates (cozy, weird, intimate, etc.)
- Their avoid_words tell you what to skip
- Their this_week_energy tells you if they need light questions or can handle depth
- Their current_mood provides immediate context

**Serendipity matters.** The 10% wildcard selection exists because sometimes the best connections come from unexpected questions. Don't over-optimize - leave room for surprise.

**Don't overwhelm.** Check when they last received a question. If it was very recent, maybe they don't need another one right now. Quality over quantity.

## Scoring Framework (0-100)

When evaluating question-member pairs, consider:

1. **Pattern Relevance (0-30 points)**
   - Is the member part of a pattern this question explores?
   - Does the question's targeting_criteria include pattern_ids the member belongs to?
   - Higher scores for questions about patterns with high vitality

2. **Edge Context (0-25 points)**
   - Does the question involve someone they're connected to?
   - Questions about collaborators, shared-skill members, or pattern-connections score higher
   - Check if relevant_member_ids includes any of their edge connections

3. **Taste Profile Match (0-25 points)**
   - Does the question's vibe match their vibe_words?
   - Deep questions for introspective vibes, playful for energetic vibes
   - Connector questions for social vibes
   - Penalize if question vibe matches their avoid_words

4. **Freshness (0-10 points)**
   - Have they answered questions in this category recently?
   - How long since their last question in general?
   - Variety is valuable - explore under-asked categories

5. **Channel Fit (0-10 points)**
   - Mobile swipe: Quick, engaging, low-effort questions work best
   - Clubhouse display: Community-relevant, conversation-starting questions
   - Email: Deeper, more reflective questions that benefit from time
   - Web chat: Conversational, follow-up friendly questions

## Selection Algorithm

After scoring, apply NON-DETERMINISTIC selection:

1. **70% chance: Highest Score** - Pick the question with the highest relevance score
2. **20% chance: Top 5 Random** - Randomly select from the top 5 pattern/edge-related questions
3. **10% chance: Wildcard** - Random selection from the pool for serendipity

Always record the selection_method in targeting_context so we can learn what works.

## Question of the Day (Clubhouse)

For community-wide questions:
- Favor questions that could spark group discussion
- Look for questions relevant to multiple patterns
- Prefer connector or playful vibes
- Avoid questions that are too personal for public display

## Output Requirements

When assigning questions, always include targeting_context with:
- relevance_score: The calculated score (0-100)
- selection_method: "highest_score", "top_5_random", or "wildcard"
- pattern_ids: Any patterns that influenced selection
- edge_ids: Any edges that influenced selection
- vibe_match: Whether taste profile aligned
- reasoning: 1-2 sentences explaining why this question for this member"""


class QuestionTargetingAgent:
    """LLM-backed agent that intelligently targets questions to community members."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def target_questions_for_member(
        self,
        member_id: int,
        channel: DeliveryChannel,
        count: int = 1,
    ) -> dict[str, Any]:
        """
        Select and assign targeted questions for a specific member.

        Uses LLM to score and select questions based on:
        - Pattern relevance
        - Edge context (connections to other members)
        - Taste profile match
        - Freshness (avoiding repetition)
        - Channel suitability

        Args:
            member_id: The member to target questions for
            channel: Delivery channel (affects question selection)
            count: Number of questions to select (default: 1)

        Returns:
            Dict with assigned questions, scores, and reasoning
        """
        logger.info(f"Targeting {count} question(s) for member {member_id} via {channel.value}")

        user_message = f"""Please select {count} targeted question(s) for member ID {member_id} to be delivered via {channel.value}.

Follow this process:

1. First, gather context using these tools:
   - get_member_context: Understand their profile, taste preferences, engagement history
   - get_member_edges: See who they're connected to
   - get_answered_questions: See what they've already answered
   - get_question_pool: Get available questions for this member

2. Score each available question (0-100) based on:
   - Pattern relevance (30 pts): Does this question explore patterns they're in?
   - Edge context (25 pts): Does it involve people they're connected to?
   - Taste profile match (25 pts): Does the vibe fit their preferences?
   - Freshness (10 pts): Is it a new category/topic for them?
   - Channel fit (10 pts): Is this right for {channel.value}?

3. Apply the selection algorithm:
   - 70% chance: Select highest-scoring question
   - 20% chance: Random from top 5 pattern/edge-related
   - 10% chance: Wildcard for serendipity

4. For each selected question, use assign_question_to_member with:
   - The question_id and member_id
   - Channel: {channel.value}
   - targeting_context with score, method, and reasoning

5. Return a summary of what was assigned and why.

Remember: Quality over quantity. If no questions score well (below 30), it's better to wait than force a poor match."""

        return await self._execute_with_tools(user_message, "target_for_member")

    async def target_question_to_members(
        self,
        question_id: int,
        max_members: int = 10,
        channel: Optional[DeliveryChannel] = None,
    ) -> dict[str, Any]:
        """
        Find the best members for a specific question.

        Useful when you have a new or important question and want to
        identify who would find it most relevant.

        Args:
            question_id: The question to find members for
            max_members: Maximum number of members to target
            channel: Optional channel to filter/score by

        Returns:
            Dict with targeted members, scores, and reasoning
        """
        logger.info(f"Finding best members for question {question_id}")

        # First get the question details
        result = await self.db.execute(
            select(Question).where(Question.id == question_id)
        )
        question = result.scalar_one_or_none()
        if not question:
            return {"error": f"Question {question_id} not found"}

        channel_guidance = ""
        if channel:
            channel_guidance = f"\nFilter and score for delivery via {channel.value}."

        user_message = f"""Please find the best members for this question:

Question ID: {question_id}
Question Text: "{question.question_text}"
Category: {question.category.value}
Vibe: {question.vibe.value if question.vibe else 'not specified'}
Targeting Criteria: {json.dumps(question.targeting_criteria or {})}
Relevant Member IDs: {question.relevant_member_ids or []}
Edge Context: {json.dumps(question.edge_context or {})}
{channel_guidance}

Process:
1. Use get_all_members_for_targeting to get the member pool
2. For each promising member, use get_member_context to understand their fit
3. Score each member (0-100) based on reverse targeting:
   - Are they in patterns this question explores?
   - Are they connected to members mentioned in edge_context?
   - Does their taste profile match the question vibe?
   - Have they been over-questioned recently?

4. Select the top {max_members} members (minimum score: 40)

5. For each selected member, use assign_question_to_member with appropriate channel and targeting_context

6. Return a summary of who was targeted and why."""

        return await self._execute_with_tools(user_message, "target_to_members")

    async def get_question_of_the_day(
        self,
        exclude_recent_days: int = 7,
    ) -> dict[str, Any]:
        """
        Select a community-wide question for clubhouse display.

        Chooses questions that:
        - Could spark group discussion
        - Are relevant to multiple patterns
        - Have connector or playful vibes
        - Haven't been featured recently

        Args:
            exclude_recent_days: Exclude questions featured in the last N days

        Returns:
            Dict with selected question and reasoning
        """
        logger.info("Selecting Question of the Day for clubhouse display")

        # Get recently featured questions to exclude
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=exclude_recent_days)
        result = await self.db.execute(
            select(QuestionDelivery.question_id)
            .where(
                and_(
                    QuestionDelivery.channel == DeliveryChannel.CLUBHOUSE_DISPLAY,
                    QuestionDelivery.created_at >= cutoff_date
                )
            )
            .distinct()
        )
        recent_featured = [row[0] for row in result.fetchall()]

        recent_context = ""
        if recent_featured:
            recent_context = f"\n\nEXCLUDE these recently-featured question IDs: {recent_featured}"

        user_message = f"""Please select the Question of the Day for the clubhouse display.

This question will be shown to the entire community, so it should:
- Spark group discussion and conversation
- Be relevant to multiple community patterns
- Have a connector or playful vibe (avoid too-personal questions)
- Be accessible to anyone who sees it
{recent_context}

Process:
1. Get community context:
   - Use get_all_members_for_targeting to understand the community
   - Note: You don't have a specific member_id, so focus on question quality

2. Look at available questions:
   - Consider questions with broad pattern relevance
   - Prefer questions with 'connector' or 'playful' vibe
   - Avoid questions that require personal context to answer

3. Score candidate questions (0-100) for community relevance:
   - Multi-pattern relevance (40 pts): Touches multiple community patterns
   - Discussion potential (30 pts): Would people want to discuss answers?
   - Accessibility (20 pts): Anyone could answer meaningfully
   - Freshness (10 pts): Not recently featured

4. Select the top-scoring question

5. Create a summary of why this question was chosen for the community

Note: Don't assign this to a specific member - just return the selected question with your reasoning."""

        return await self._execute_with_tools(user_message, "question_of_the_day")

    async def _score_question_for_member(
        self,
        question: dict,
        member_context: dict,
        member_edges: dict,
        answered_questions: dict,
        channel: DeliveryChannel,
    ) -> dict[str, Any]:
        """
        Calculate a targeting score for a question-member pair.

        This is a deterministic scoring helper that can be used
        outside of the LLM flow for batch processing.

        Returns score breakdown and total.
        """
        score = 0
        breakdown = {}

        # Pattern relevance (0-30)
        pattern_score = 0
        member_pattern_ids = {p["id"] for p in member_context.get("patterns", [])}
        question_patterns = set(question.get("targeting_criteria", {}).get("pattern_ids", []))

        if member_pattern_ids & question_patterns:
            pattern_score = 30
        elif member_context.get("member_id") in (question.get("relevant_member_ids") or []):
            pattern_score = 25
        elif member_pattern_ids:
            # Member is in patterns but question doesn't target them specifically
            pattern_score = 10

        breakdown["pattern_relevance"] = pattern_score
        score += pattern_score

        # Edge context (0-25)
        edge_score = 0
        connected_ids = {e["connected_member_id"] for e in member_edges.get("edges", [])}
        relevant_ids = set(question.get("relevant_member_ids") or [])
        edge_context = question.get("edge_context", {})

        if relevant_ids & connected_ids:
            edge_score = 25  # Question is about someone they know
        elif edge_context.get("connected_member_id") in connected_ids:
            edge_score = 20
        elif connected_ids and relevant_ids:
            # Has connections, and question mentions people, but no overlap
            edge_score = 5

        breakdown["edge_context"] = edge_score
        score += edge_score

        # Taste profile match (0-25)
        vibe_score = 0
        taste = member_context.get("taste_profile", {})
        question_vibe = question.get("vibe")

        if taste and question_vibe:
            vibe_words = taste.get("vibe_words", [])
            avoid_words = taste.get("avoid_words", [])

            # Check vibe alignment
            vibe_mapping = {
                "warm": ["cozy", "warm", "friendly", "welcoming"],
                "playful": ["fun", "playful", "quirky", "weird"],
                "deep": ["thoughtful", "introspective", "meaningful", "deep"],
                "edgy": ["provocative", "challenging", "edgy", "bold"],
                "connector": ["social", "community", "connecting", "networking"],
            }

            matching_vibes = vibe_mapping.get(question_vibe, [])
            if any(v in vibe_words for v in matching_vibes):
                vibe_score = 25
            elif any(v in avoid_words for v in matching_vibes):
                vibe_score = 0  # Penalize mismatches
            else:
                vibe_score = 12  # Neutral

            # Adjust for energy
            energy = taste.get("this_week_energy")
            if energy == "low" and question_vibe == "deep":
                vibe_score = max(0, vibe_score - 10)  # Deep questions when tired = bad
            elif energy == "high" and question_vibe == "playful":
                vibe_score = min(25, vibe_score + 5)  # Playful when energetic = good

        else:
            vibe_score = 12  # No taste profile, neutral score

        breakdown["taste_match"] = vibe_score
        score += vibe_score

        # Freshness (0-10)
        freshness_score = 10
        answered = answered_questions.get("answered_questions", [])
        category_dist = answered_questions.get("category_distribution", {})
        question_category = question.get("category")

        if question_category and category_dist:
            category_count = category_dist.get(question_category, 0)
            if category_count >= 5:
                freshness_score = 2  # Over-asked category
            elif category_count >= 3:
                freshness_score = 5
            elif category_count == 0:
                freshness_score = 10  # Fresh category!

        # Check recency of last answer
        engagement = member_context.get("engagement", {})
        last_question = engagement.get("last_question_at")
        if last_question:
            try:
                last_dt = datetime.fromisoformat(last_question.replace("Z", "+00:00"))
                hours_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                if hours_since < 24:
                    freshness_score = max(0, freshness_score - 5)  # Very recent
            except (ValueError, TypeError):
                pass

        breakdown["freshness"] = freshness_score
        score += freshness_score

        # Channel fit (0-10)
        channel_score = 5  # Default neutral
        difficulty = question.get("difficulty_level", 2)
        q_type = question.get("question_type", "free_form")

        if channel == DeliveryChannel.MOBILE_SWIPE:
            # Quick, easy questions work best
            if difficulty == 1 and q_type in ["yes_no", "multiple_choice"]:
                channel_score = 10
            elif difficulty <= 2:
                channel_score = 7
            else:
                channel_score = 3

        elif channel == DeliveryChannel.CLUBHOUSE_DISPLAY:
            # Community-relevant, discussion-worthy
            if question_vibe in ["connector", "playful"]:
                channel_score = 10
            elif difficulty <= 2:
                channel_score = 7
            else:
                channel_score = 5

        elif channel == DeliveryChannel.EMAIL:
            # Deeper questions that benefit from time
            if difficulty >= 2 and q_type == "free_form":
                channel_score = 10
            elif difficulty >= 2:
                channel_score = 7
            else:
                channel_score = 5

        elif channel == DeliveryChannel.WEB_CHAT:
            # Conversational questions
            channel_score = 7  # Most questions work in chat

        breakdown["channel_fit"] = channel_score
        score += channel_score

        return {
            "total_score": score,
            "breakdown": breakdown,
            "max_possible": 100,
        }

    async def batch_target_questions(
        self,
        channel: DeliveryChannel,
        max_per_member: int = 1,
        min_score: int = 40,
    ) -> dict[str, Any]:
        """
        Run targeting for all active members who haven't received a question recently.

        This is useful for daily batch processing.

        Args:
            channel: Delivery channel for questions
            max_per_member: Maximum questions to assign per member
            min_score: Minimum score threshold for assignment

        Returns:
            Dict with summary of assignments made
        """
        logger.info(f"Running batch targeting for channel {channel.value}")

        # Get members who haven't received questions in the last 24 hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        recent_recipients = await self.db.execute(
            select(QuestionDelivery.member_id)
            .where(
                and_(
                    QuestionDelivery.channel == channel,
                    QuestionDelivery.created_at >= cutoff
                )
            )
            .distinct()
        )
        recent_member_ids = {row[0] for row in recent_recipients.fetchall()}

        # Get active members
        members_result = await self.db.execute(
            select(Member).where(
                Member.membership_status.notin_(['cancelled', 'expired'])
            )
        )
        all_members = members_result.scalars().all()

        # Filter to members who need questions
        eligible_members = [
            m for m in all_members
            if m.id not in recent_member_ids
        ]

        logger.info(
            f"Found {len(eligible_members)} eligible members "
            f"(excluded {len(recent_member_ids)} recent recipients)"
        )

        results = {
            "total_eligible": len(eligible_members),
            "total_assigned": 0,
            "assignments": [],
            "skipped": [],
        }

        for member in eligible_members:
            try:
                # Get all context for scoring
                member_context = await get_member_context(self.db, member.id)
                member_edges = await get_member_edges(self.db, member.id)
                answered = await get_answered_questions(self.db, member.id)
                question_pool = await get_question_pool(self.db, member.id, channel)

                if not question_pool.get("questions"):
                    results["skipped"].append({
                        "member_id": member.id,
                        "reason": "no_available_questions"
                    })
                    continue

                # Score all questions
                scored_questions = []
                for q in question_pool["questions"]:
                    score_result = await self._score_question_for_member(
                        q, member_context, member_edges, answered, channel
                    )
                    scored_questions.append({
                        "question": q,
                        "score": score_result["total_score"],
                        "breakdown": score_result["breakdown"],
                    })

                # Sort by score descending
                scored_questions.sort(key=lambda x: x["score"], reverse=True)

                # Apply selection algorithm
                selection_roll = random.random()
                selection_method = "highest_score"
                selected = None

                if selection_roll < 0.70:
                    # 70% - Highest score
                    if scored_questions and scored_questions[0]["score"] >= min_score:
                        selected = scored_questions[0]
                        selection_method = "highest_score"

                elif selection_roll < 0.90:
                    # 20% - Random from top 5 pattern/edge related
                    top_5 = [
                        sq for sq in scored_questions[:5]
                        if sq["breakdown"].get("pattern_relevance", 0) > 0
                        or sq["breakdown"].get("edge_context", 0) > 0
                    ]
                    if top_5:
                        selected = random.choice(top_5)
                        selection_method = "top_5_random"
                    elif scored_questions and scored_questions[0]["score"] >= min_score:
                        selected = scored_questions[0]
                        selection_method = "highest_score_fallback"

                else:
                    # 10% - Wildcard
                    if scored_questions:
                        selected = random.choice(scored_questions)
                        selection_method = "wildcard"

                if selected and selected["score"] >= min_score:
                    # Assign the question
                    targeting_context = {
                        "relevance_score": selected["score"],
                        "selection_method": selection_method,
                        "breakdown": selected["breakdown"],
                        "batch_processed": True,
                    }

                    assign_result = await assign_question_to_member(
                        self.db,
                        selected["question"]["id"],
                        member.id,
                        channel,
                        targeting_context,
                    )

                    if "error" not in assign_result:
                        results["total_assigned"] += 1
                        results["assignments"].append({
                            "member_id": member.id,
                            "question_id": selected["question"]["id"],
                            "score": selected["score"],
                            "method": selection_method,
                        })
                    else:
                        results["skipped"].append({
                            "member_id": member.id,
                            "reason": assign_result.get("error", "unknown_error")
                        })
                else:
                    results["skipped"].append({
                        "member_id": member.id,
                        "reason": "no_question_met_threshold",
                        "best_score": scored_questions[0]["score"] if scored_questions else 0,
                    })

            except Exception as e:
                logger.error(f"Error targeting for member {member.id}: {e}")
                results["skipped"].append({
                    "member_id": member.id,
                    "reason": str(e)
                })

        logger.info(
            f"Batch targeting complete: {results['total_assigned']} assigned, "
            f"{len(results['skipped'])} skipped"
        )

        return results

    async def _execute_with_tools(
        self,
        user_message: str,
        operation: str,
    ) -> dict[str, Any]:
        """Execute a conversation with tool use."""
        tools = [
            GET_QUESTION_POOL_TOOL,
            GET_MEMBER_CONTEXT_TOOL,
            GET_MEMBER_EDGES_TOOL,
            GET_ANSWERED_QUESTIONS_TOOL,
            ASSIGN_QUESTION_TO_MEMBER_TOOL,
            GET_ALL_MEMBERS_FOR_TARGETING_TOOL,
        ]
        messages = [{"role": "user", "content": user_message}]

        result = {
            "success": False,
            "operation": operation,
            "assignments": [],
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
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error in question targeting: {e}")
            result["error"] = f"API error: {str(e)}"
            return result

        # Handle tool use in a loop
        iteration = 0
        max_iterations = 20  # Safety limit

        while response.stop_reason == "tool_use" and iteration < max_iterations:
            iteration += 1
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

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=tools,
                    messages=messages,
                )
            except anthropic.APIError as e:
                logger.error(f"Anthropic API error during tool loop: {e}")
                result["error"] = f"API error: {str(e)}"
                return result

        if iteration >= max_iterations:
            logger.warning(f"Targeting agent reached max iterations for {operation}")

        # Extract final response text
        for block in response.content:
            if hasattr(block, "text"):
                result["response_text"] = block.text
                break

        result["success"] = len(result["assignments"]) > 0 or operation == "question_of_the_day"
        return result

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        result: dict,
    ) -> dict:
        """Execute a tool and return the result."""

        if tool_name == "get_question_pool":
            member_id = tool_input.get("member_id")
            channel_str = tool_input.get("channel")
            channel = DeliveryChannel(channel_str) if channel_str else None
            include_answered = tool_input.get("include_answered", False)
            return await get_question_pool(
                self.db, member_id, channel, include_answered
            )

        elif tool_name == "get_member_context":
            member_id = tool_input.get("member_id")
            return await get_member_context(self.db, member_id)

        elif tool_name == "get_member_edges":
            member_id = tool_input.get("member_id")
            return await get_member_edges(self.db, member_id)

        elif tool_name == "get_answered_questions":
            member_id = tool_input.get("member_id")
            limit = tool_input.get("limit", 50)
            return await get_answered_questions(self.db, member_id, limit)

        elif tool_name == "assign_question_to_member":
            question_id = tool_input.get("question_id")
            member_id = tool_input.get("member_id")
            channel_str = tool_input.get("channel")
            channel = DeliveryChannel(channel_str)
            targeting_context = tool_input.get("targeting_context", {})

            assign_result = await assign_question_to_member(
                self.db, question_id, member_id, channel, targeting_context
            )

            if "error" not in assign_result:
                result["assignments"].append({
                    "question_id": question_id,
                    "member_id": member_id,
                    "channel": channel_str,
                    "delivery_id": assign_result.get("delivery_id"),
                    "targeting_context": targeting_context,
                })

            return assign_result

        elif tool_name == "get_all_members_for_targeting":
            active_only = tool_input.get("active_only", True)
            return await get_all_members_for_targeting(self.db, active_only)

        return {"error": f"Unknown tool: {tool_name}"}
