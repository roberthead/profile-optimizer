"""
Clubhouse Digital Display Endpoints

These endpoints power the clubhouse TV display, showing community highlights
like the question of the day, pattern spotlights, and recent connections.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Tuple
from datetime import datetime, timedelta, timezone, date
import hashlib
import logging

from app.core.database import get_db
from app.models import (
    Member,
    Question,
    QuestionResponse,
    Pattern,
    MemberEdge,
    PatternCategory,
    EdgeType,
)
from app.agents.group_question import GroupQuestionAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/display", tags=["display"])

# =============================================================================
# Cache for display endpoints (5 minute TTL)
# =============================================================================
_display_cache: dict[str, Tuple[datetime, dict]] = {}
DISPLAY_CACHE_TTL = 300  # 5 minutes


def _get_display_cache(key: str) -> Optional[dict]:
    """Get cached data if not expired."""
    if key in _display_cache:
        cached_time, data = _display_cache[key]
        if datetime.now() - cached_time < timedelta(seconds=DISPLAY_CACHE_TTL):
            return data
        del _display_cache[key]
    return None


def _set_display_cache(key: str, data: dict) -> None:
    """Store data in cache."""
    _display_cache[key] = (datetime.now(), data)


def _clear_display_cache() -> int:
    """Clear all display cache entries."""
    global _display_cache
    count = len(_display_cache)
    _display_cache = {}
    return count


# =============================================================================
# Response Models
# =============================================================================

class RecentAnswerResponse(BaseModel):
    text: str
    member_name: str
    timestamp: datetime

    class Config:
        from_attributes = True


class QuestionOfTheDayResponse(BaseModel):
    question_id: int
    question: str
    context: str
    category: str
    recent_answers: List[RecentAnswerResponse]

    class Config:
        from_attributes = True


class PatternMemberResponse(BaseModel):
    name: str
    role: Optional[str]

    class Config:
        from_attributes = True


class PatternSpotlightResponse(BaseModel):
    pattern_id: int
    pattern: str
    description: str
    category: str
    members: List[PatternMemberResponse]
    sample_questions: List[str]
    vitality_score: float

    class Config:
        from_attributes = True


class ConnectionResponse(BaseModel):
    member_a_name: str
    member_b_name: str
    edge_type: str
    discovered_at: datetime

    class Config:
        from_attributes = True


class RecentConnectionsResponse(BaseModel):
    connections: List[ConnectionResponse]

    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    title: str
    venue: Optional[str]
    date: Optional[datetime]
    category: Optional[str]
    tags: List[str]

    class Config:
        from_attributes = True


class RecommendedEventsResponse(BaseModel):
    events: List[EventResponse]
    source: str  # "rova" or "placeholder"

    class Config:
        from_attributes = True


class DisplayStatsResponse(BaseModel):
    member_count: int
    edge_count: int
    pattern_count: int
    questions_answered_this_week: int

    class Config:
        from_attributes = True


# =============================================================================
# Helper Functions
# =============================================================================

def get_daily_seed() -> int:
    """Generate a consistent seed based on today's date for daily rotation."""
    today = date.today().isoformat()
    return int(hashlib.md5(today.encode()).hexdigest()[:8], 16)


def get_weekly_seed() -> int:
    """Generate a consistent seed based on the current week for weekly rotation."""
    today = date.today()
    # Get Monday of current week
    week_start = today - timedelta(days=today.weekday())
    return int(hashlib.md5(week_start.isoformat().encode()).hexdigest()[:8], 16)


def get_member_display_name(member: Member, first_name_only: bool = True) -> str:
    """Get a display-safe name for a member."""
    if first_name_only:
        return member.first_name or "Anonymous"
    if member.first_name and member.last_name:
        return f"{member.first_name} {member.last_name[0]}."
    return member.first_name or "Anonymous"


def get_edge_type_display(edge_type: EdgeType) -> str:
    """Get human-readable edge type."""
    display_map = {
        EdgeType.SHARED_SKILL: "shared skills",
        EdgeType.SHARED_INTEREST: "shared interests",
        EdgeType.COLLABORATION_POTENTIAL: "collaboration potential",
        EdgeType.EVENT_CO_ATTENDANCE: "event co-attendance",
        EdgeType.INTRODUCED_BY_AGENT: "agent introduction",
        EdgeType.PATTERN_CONNECTION: "pattern connection",
    }
    return display_map.get(edge_type, str(edge_type.value))


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/question-of-the-day", response_model=QuestionOfTheDayResponse)
async def get_question_of_the_day(
    skip_cache: bool = Query(False, description="Skip cache"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a featured question that rotates daily.

    Selection logic:
    - Prioritizes questions with recent engagement
    - Uses daily seed for consistent rotation throughout the day
    - Falls back to any active question if none have responses

    Results cached for 5 minutes.
    """
    # Check cache first
    cache_key = "question_of_the_day"
    if not skip_cache:
        cached = _get_display_cache(cache_key)
        if cached:
            return QuestionOfTheDayResponse(**cached)

    # Get all active questions with their response counts
    query = (
        select(
            Question,
            func.count(QuestionResponse.id).label("response_count")
        )
        .outerjoin(QuestionResponse, Question.id == QuestionResponse.question_id)
        .where(Question.is_active == True)
        .group_by(Question.id)
        .order_by(func.count(QuestionResponse.id).desc())
    )

    result = await db.execute(query)
    questions_with_counts = result.all()

    if not questions_with_counts:
        raise HTTPException(
            status_code=404,
            detail="No questions available. Generate a question deck first."
        )

    # Use daily seed to select from top questions
    seed = get_daily_seed()
    # Prefer questions with engagement, but include all for variety
    top_questions = [q for q, count in questions_with_counts if count > 0]
    if not top_questions:
        top_questions = [q for q, _ in questions_with_counts]

    selected_question = top_questions[seed % len(top_questions)]

    # Get recent answers (last 5)
    answers_query = (
        select(QuestionResponse, Member)
        .join(Member, QuestionResponse.member_id == Member.id)
        .where(QuestionResponse.question_id == selected_question.id)
        .order_by(QuestionResponse.created_at.desc())
        .limit(5)
    )

    answers_result = await db.execute(answers_query)
    recent_answers = [
        RecentAnswerResponse(
            text=response.response_text[:200] + "..." if len(response.response_text) > 200 else response.response_text,
            member_name=get_member_display_name(member),
            timestamp=response.created_at
        )
        for response, member in answers_result.all()
    ]

    # Build context
    context = selected_question.purpose or f"Exploring {selected_question.category.value.replace('_', ' ')}"
    if selected_question.notes:
        context = selected_question.notes

    response = QuestionOfTheDayResponse(
        question_id=selected_question.id,
        question=selected_question.question_text,
        context=context,
        category=selected_question.category.value,
        recent_answers=recent_answers
    )
    _set_display_cache(cache_key, response.model_dump())
    return response


@router.get("/pattern-spotlight", response_model=PatternSpotlightResponse)
async def get_pattern_spotlight(
    skip_cache: bool = Query(False, description="Skip cache"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a featured pattern that rotates weekly.

    Selection logic:
    - Prioritizes patterns with good vitality_score
    - Uses weekly seed for consistent rotation throughout the week
    - Shows member names in the pattern

    Results cached for 5 minutes.
    """
    cache_key = "pattern_spotlight"
    if not skip_cache:
        cached = _get_display_cache(cache_key)
        if cached:
            return PatternSpotlightResponse(**cached)

    # Get active patterns ordered by vitality
    query = (
        select(Pattern)
        .where(Pattern.is_active == True)
        .order_by(Pattern.vitality_score.desc(), Pattern.member_count.desc())
    )

    result = await db.execute(query)
    patterns = result.scalars().all()

    if not patterns:
        raise HTTPException(
            status_code=404,
            detail="No patterns discovered yet. Run pattern discovery first."
        )

    # Use weekly seed to select from top patterns (top 50% by vitality)
    seed = get_weekly_seed()
    top_count = max(1, len(patterns) // 2)
    top_patterns = patterns[:top_count]
    selected_pattern = top_patterns[seed % len(top_patterns)]

    # Get members in this pattern
    members = []
    if selected_pattern.related_member_ids:
        members_query = (
            select(Member)
            .where(Member.id.in_(selected_pattern.related_member_ids))
            .limit(10)  # Limit for display
        )
        members_result = await db.execute(members_query)
        members = [
            PatternMemberResponse(
                name=get_member_display_name(member, first_name_only=False),
                role=member.role
            )
            for member in members_result.scalars().all()
        ]

    # Get sample questions (from question_prompts or generate from evidence)
    sample_questions = selected_pattern.question_prompts or []
    if not sample_questions and selected_pattern.evidence:
        # Generate placeholder questions from evidence
        evidence = selected_pattern.evidence
        if "shared_skills" in evidence:
            skills = evidence["shared_skills"][:3] if isinstance(evidence["shared_skills"], list) else []
            for skill in skills:
                sample_questions.append(f"How do you use {skill} in your work?")
        if "shared_interests" in evidence:
            interests = evidence["shared_interests"][:2] if isinstance(evidence["shared_interests"], list) else []
            for interest in interests:
                sample_questions.append(f"What draws you to {interest}?")

    response = PatternSpotlightResponse(
        pattern_id=selected_pattern.id,
        pattern=selected_pattern.name,
        description=selected_pattern.description,
        category=selected_pattern.category.value,
        members=members,
        sample_questions=sample_questions[:5],  # Limit to 5
        vitality_score=selected_pattern.vitality_score
    )
    _set_display_cache(cache_key, response.model_dump())
    return response


@router.get("/recent-connections", response_model=RecentConnectionsResponse)
async def get_recent_connections(
    days: int = 7,
    limit: int = 10,
    skip_cache: bool = Query(False, description="Skip cache"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns recently discovered member edges.

    Uses first names only for privacy on public display.
    Results cached for 5 minutes.
    """
    cache_key = f"recent_connections_{days}_{limit}"
    if not skip_cache:
        cached = _get_display_cache(cache_key)
        if cached:
            return RecentConnectionsResponse(**cached)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Fetch edges
    edges_query = (
        select(MemberEdge)
        .where(MemberEdge.created_at >= cutoff)
        .where(MemberEdge.is_active == True)
        .order_by(MemberEdge.created_at.desc())
        .limit(limit)
    )
    edges_result = await db.execute(edges_query)
    edges = edges_result.scalars().all()

    if not edges:
        response = RecentConnectionsResponse(connections=[])
        _set_display_cache(cache_key, response.model_dump())
        return response

    # Collect all member IDs needed (batch fetch instead of N+1)
    member_ids = set()
    for edge in edges:
        member_ids.add(edge.member_a_id)
        member_ids.add(edge.member_b_id)

    # Fetch all members in one query
    members_result = await db.execute(
        select(Member).where(Member.id.in_(member_ids))
    )
    members_map = {m.id: m for m in members_result.scalars().all()}

    # Build connections
    connections = []
    for edge in edges:
        member_a = members_map.get(edge.member_a_id)
        member_b = members_map.get(edge.member_b_id)

        if member_a and member_b:
            connections.append(
                ConnectionResponse(
                    member_a_name=get_member_display_name(member_a),
                    member_b_name=get_member_display_name(member_b),
                    edge_type=get_edge_type_display(edge.edge_type),
                    discovered_at=edge.created_at
                )
            )

    response = RecentConnectionsResponse(connections=connections)
    _set_display_cache(cache_key, response.model_dump())
    return response


@router.get("/recommended-events", response_model=RecommendedEventsResponse)
async def get_recommended_events(
    limit: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns upcoming events from Rova (if integrated).

    Currently returns placeholder data. When Rova integration is complete,
    this will fetch real community events.
    """
    # TODO: Integrate with Rova API when available
    # For now, return placeholder indicating integration needed

    return RecommendedEventsResponse(
        events=[
            EventResponse(
                title="Rova Integration Coming Soon",
                venue="White Rabbit Ashland",
                date=datetime.now(timezone.utc) + timedelta(days=7),
                category="Community",
                tags=["placeholder", "coming-soon"]
            )
        ],
        source="placeholder"
    )


class GroupContextRequest(BaseModel):
    """Optional context for group question selection."""
    time_of_day: Optional[str] = None  # "morning", "afternoon", "evening", "night"
    day_of_week: Optional[str] = None  # "Monday", "Tuesday", etc.
    meeting_name: Optional[str] = None  # "AI Cohort", "Creator Workshop", etc.
    present_member_ids: Optional[List[int]] = None  # Members currently present


class GroupQuestionResponse(BaseModel):
    question_id: int
    question: str
    context: str
    category: str
    vibe: Optional[str]
    targeting_reason: str
    suggested_for_members: List[str]
    recent_answers: List[RecentAnswerResponse]

    class Config:
        from_attributes = True


@router.post("/group-question", response_model=GroupQuestionResponse)
async def get_group_question(
    context: GroupContextRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a question tailored to the group present, using the GroupQuestionAgent.

    The LLM agent analyzes:
    - Profiles and relationships of present members
    - Time of day and meeting context
    - Recent questions to avoid repetition
    - Collective group vibe

    Falls back to heuristic selection if agent fails.
    """
    import random

    # Determine time context
    now = datetime.now()
    hour = now.hour
    day_of_week = context.day_of_week if context and context.day_of_week else now.strftime("%A")

    if context and context.time_of_day:
        time_of_day = context.time_of_day
    elif hour < 12:
        time_of_day = "morning"
    elif hour < 17:
        time_of_day = "afternoon"
    elif hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "night"

    # Try to use the GroupQuestionAgent if we have present members
    use_agent = (
        context and
        context.present_member_ids and
        len(context.present_member_ids) >= 2
    )

    selected_question = None
    targeting_reason = ""
    suggested_member_ids = []

    if use_agent:
        try:
            # Map meeting name to meeting type
            meeting_type = "casual"
            if context.meeting_name:
                meeting_key = context.meeting_name.lower()
                if "cohort" in meeting_key or "workshop" in meeting_key:
                    meeting_type = "workshop"
                elif "dinner" in meeting_key or "social" in meeting_key:
                    meeting_type = "social"
                elif "demo" in meeting_key:
                    meeting_type = "demo_day"
                elif "retreat" in meeting_key:
                    meeting_type = "retreat"

            agent_context = {
                "time_of_day": time_of_day,
                "day_of_week": day_of_week,
                "meeting_type": meeting_type,
                "meeting_name": context.meeting_name,
            }

            agent = GroupQuestionAgent(db)
            result = await agent.select_group_question(
                context=agent_context,
                present_member_ids=context.present_member_ids,
                db=db
            )

            if result.get("success") and result.get("question_id"):
                # Agent succeeded - fetch the question
                q_result = await db.execute(
                    select(Question).where(Question.id == result["question_id"])
                )
                selected_question = q_result.scalar_one_or_none()
                targeting_reason = result.get("targeting_reason", "")
                suggested_member_ids = result.get("suggested_for_members", [])

                logger.info(f"GroupQuestionAgent selected question {result['question_id']}")
        except Exception as e:
            logger.warning(f"GroupQuestionAgent failed, using fallback: {e}")

    # Fallback to heuristic selection if agent didn't provide a question
    if not selected_question:
        # Map time to preferred question vibes
        time_vibe_preferences = {
            "morning": ["warm", "playful"],
            "afternoon": ["connector", "warm"],
            "evening": ["deep", "connector"],
            "night": ["edgy", "deep"],
        }
        preferred_vibes = time_vibe_preferences.get(time_of_day, ["warm"])

        # Map meetings to preferred categories
        meeting_category_hints = {
            "ai cohort": ["collaboration", "future_vision", "hidden_depths"],
            "creator workshop": ["creative_spark", "origin_story", "impact_legacy"],
            "startup office hours": ["future_vision", "collaboration"],
            "community dinner": ["community_connection", "origin_story"],
            "social hour": ["playful", "community_connection"],
            "demo day": ["impact_legacy", "creative_spark"],
        }

        preferred_categories = []
        if context and context.meeting_name:
            meeting_key = context.meeting_name.lower()
            for key, cats in meeting_category_hints.items():
                if key in meeting_key:
                    preferred_categories = cats
                    break

        # Build query for questions
        query = select(Question).where(Question.is_active == True)
        result = await db.execute(query)
        all_questions = result.scalars().all()

        if not all_questions:
            raise HTTPException(status_code=404, detail="No questions available")

        # Score questions based on context
        scored_questions = []
        for q in all_questions:
            score = 50  # Base score

            # Boost for matching vibe
            if q.vibe and q.vibe.value in preferred_vibes:
                score += 25

            # Boost for matching category (if meeting context provided)
            if preferred_categories and q.category.value in preferred_categories:
                score += 30

            # Boost for connector questions when multiple people present
            if context and context.present_member_ids and len(context.present_member_ids) > 2:
                if q.vibe and q.vibe.value == "connector":
                    score += 20

            # Lower difficulty in morning, higher at night
            if time_of_day == "morning" and q.difficulty_level == 1:
                score += 10
            elif time_of_day == "night" and q.difficulty_level == 3:
                score += 10

            # Add randomness for variety
            score += random.randint(0, 15)

            scored_questions.append((q, score))

        # Sort by score and pick from top
        scored_questions.sort(key=lambda x: x[1], reverse=True)
        top_questions = scored_questions[:5]

        # Weighted random selection from top 5
        total_score = sum(score for _, score in top_questions)
        rand_val = random.uniform(0, total_score)
        cumulative = 0
        selected_question = top_questions[0][0]

        for q, score in top_questions:
            cumulative += score
            if rand_val <= cumulative:
                selected_question = q
                break

        # Build fallback targeting reason
        targeting_parts = []
        if time_of_day:
            targeting_parts.append(f"{time_of_day} timing")
        if context and context.meeting_name:
            targeting_parts.append(f"for {context.meeting_name}")
        if preferred_vibes and selected_question.vibe:
            targeting_parts.append(f"{selected_question.vibe.value} vibe")

        targeting_reason = "Selected based on " + ", ".join(targeting_parts) if targeting_parts else "General community question"

    # Get recent answers
    answers_query = (
        select(QuestionResponse, Member)
        .join(Member, QuestionResponse.member_id == Member.id)
        .where(QuestionResponse.question_id == selected_question.id)
        .order_by(QuestionResponse.created_at.desc())
        .limit(5)
    )
    answers_result = await db.execute(answers_query)
    recent_answers = [
        RecentAnswerResponse(
            text=r.response_text[:200] + "..." if len(r.response_text) > 200 else r.response_text,
            member_name=get_member_display_name(m),
            timestamp=r.created_at
        )
        for r, m in answers_result.all()
    ]

    # Determine suggested members
    suggested_members = []
    member_ids_to_fetch = suggested_member_ids or (selected_question.relevant_member_ids or [])
    if member_ids_to_fetch:
        members_query = (
            select(Member)
            .where(Member.id.in_(member_ids_to_fetch))
            .limit(5)
        )
        members_result = await db.execute(members_query)
        suggested_members = [get_member_display_name(m) for m in members_result.scalars().all()]

    return GroupQuestionResponse(
        question_id=selected_question.id,
        question=selected_question.question_text,
        context=selected_question.notes or selected_question.purpose or f"Exploring {selected_question.category.value}",
        category=selected_question.category.value,
        vibe=selected_question.vibe.value if selected_question.vibe else None,
        targeting_reason=targeting_reason,
        suggested_for_members=suggested_members,
        recent_answers=recent_answers
    )


@router.get("/stats", response_model=DisplayStatsResponse)
async def get_display_stats(
    skip_cache: bool = Query(False, description="Skip cache"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns community graph stats for display.
    Results cached for 5 minutes.
    """
    cache_key = "display_stats"
    if not skip_cache:
        cached = _get_display_cache(cache_key)
        if cached:
            return DisplayStatsResponse(**cached)

    # Count active members (exclude cancelled/expired)
    member_count_result = await db.execute(
        select(func.count(Member.id))
        .where(Member.membership_status.notin_(['cancelled', 'expired']))
    )
    member_count = member_count_result.scalar() or 0

    # Count active edges
    edge_count_result = await db.execute(
        select(func.count(MemberEdge.id))
        .where(MemberEdge.is_active == True)
    )
    edge_count = edge_count_result.scalar() or 0

    # Count active patterns
    pattern_count_result = await db.execute(
        select(func.count(Pattern.id))
        .where(Pattern.is_active == True)
    )
    pattern_count = pattern_count_result.scalar() or 0

    # Count questions answered this week
    week_ago = datetime.now(timezone.utc) - timedelta(weeks=1)
    questions_answered_result = await db.execute(
        select(func.count(QuestionResponse.id))
        .where(QuestionResponse.created_at >= week_ago)
    )
    questions_answered_this_week = questions_answered_result.scalar() or 0

    response = DisplayStatsResponse(
        member_count=member_count,
        edge_count=edge_count,
        pattern_count=pattern_count,
        questions_answered_this_week=questions_answered_this_week
    )
    _set_display_cache(cache_key, response.model_dump())
    return response


@router.post("/cache/clear")
async def clear_display_cache():
    """Clear all display data cache. Use after major data changes."""
    count = _clear_display_cache()
    return {"message": f"Cleared {count} cached display entries"}
