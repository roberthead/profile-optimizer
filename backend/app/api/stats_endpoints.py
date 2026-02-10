"""Data model statistics API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Any, Tuple
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.models import (
    Member, MemberEdge, TasteProfile, Pattern, Question,
    QuestionDelivery, EventSignal, QuestionResponse,
    EdgeType, DeliveryStatus
)

router = APIRouter(prefix="/stats", tags=["stats"])

# Simple in-memory cache for model stats
_model_cache: Optional[Tuple[datetime, dict]] = None
MODEL_CACHE_TTL_SECONDS = 300  # 5 minutes


class TableInfo(BaseModel):
    """Information about a database table."""
    name: str
    count: int
    sample: Optional[dict] = None


class Relationship(BaseModel):
    """A relationship between two tables."""
    from_table: str
    to_table: str
    type: str  # "1:1", "1:N"


class ModelStatsResponse(BaseModel):
    """Complete data model statistics."""
    tables: List[TableInfo]
    relationships: List[Relationship]


class Activity(BaseModel):
    """A recent activity in the system."""
    type: str
    description: str
    timestamp: datetime


class ActivityFeedResponse(BaseModel):
    """Recent activity feed."""
    activities: List[Activity]


def member_to_sample(member: Member) -> dict:
    """Convert a member to a sample dict."""
    return {
        "id": member.id,
        "first_name": member.first_name,
        "last_name": member.last_name,
        "email": member.email,
        "membership_status": member.membership_status,
        "skills": (member.skills or [])[:3],
        "interests": (member.interests or [])[:3],
    }


def edge_to_sample(edge: MemberEdge) -> dict:
    """Convert an edge to a sample dict."""
    return {
        "id": edge.id,
        "member_a_id": edge.member_a_id,
        "member_b_id": edge.member_b_id,
        "edge_type": edge.edge_type.value,
        "strength": edge.strength,
        "discovered_via": edge.discovered_via,
    }


def taste_profile_to_sample(tp: TasteProfile) -> dict:
    """Convert a taste profile to a sample dict."""
    return {
        "id": tp.id,
        "member_id": tp.member_id,
        "vibe_words": (tp.vibe_words or [])[:3],
        "energy_time": tp.energy_time,
        "spontaneity": tp.spontaneity,
    }


def pattern_to_sample(pattern: Pattern) -> dict:
    """Convert a pattern to a sample dict."""
    return {
        "id": pattern.id,
        "name": pattern.name,
        "category": pattern.category.value,
        "member_count": pattern.member_count,
        "vitality_score": pattern.vitality_score,
    }


def question_to_sample(question: Question) -> dict:
    """Convert a question to a sample dict."""
    return {
        "id": question.id,
        "question_text": question.question_text[:100] + "..." if len(question.question_text) > 100 else question.question_text,
        "category": question.category.value,
        "question_type": question.question_type.value,
        "difficulty_level": question.difficulty_level,
    }


def delivery_to_sample(delivery: QuestionDelivery) -> dict:
    """Convert a question delivery to a sample dict."""
    return {
        "id": delivery.id,
        "question_id": delivery.question_id,
        "member_id": delivery.member_id,
        "channel": delivery.channel.value,
        "delivery_status": delivery.delivery_status.value,
    }


def signal_to_sample(signal: EventSignal) -> dict:
    """Convert an event signal to a sample dict."""
    return {
        "id": signal.id,
        "member_id": signal.member_id,
        "rova_event_id": signal.rova_event_id,
        "signal_type": signal.signal_type.value,
        "signal_strength": signal.signal_strength,
    }


def response_to_sample(response: QuestionResponse) -> dict:
    """Convert a question response to a sample dict."""
    return {
        "id": response.id,
        "question_id": response.question_id,
        "member_id": response.member_id,
        "response_text": response.response_text[:100] + "..." if len(response.response_text) > 100 else response.response_text,
        "led_to_suggestion": response.led_to_suggestion,
    }


@router.get("/model", response_model=ModelStatsResponse)
async def get_model_stats(
    skip_cache: bool = Query(False, description="Skip cache and fetch fresh data"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get data model statistics including table counts and sample data.

    Returns counts and sample data for all main entities in the system.
    Results are cached for 5 minutes.
    """
    global _model_cache

    # Check cache first
    if not skip_cache and _model_cache is not None:
        cached_time, cached_data = _model_cache
        if datetime.now() - cached_time < timedelta(seconds=MODEL_CACHE_TTL_SECONDS):
            return ModelStatsResponse(**cached_data)

    # Get counts for all tables
    tables_data = []

    # Members
    members_count_result = await db.execute(
        select(func.count(Member.id)).where(
            Member.membership_status.notin_(['cancelled', 'expired'])
        )
    )
    members_count = members_count_result.scalar() or 0

    members_sample_result = await db.execute(
        select(Member).where(
            Member.membership_status.notin_(['cancelled', 'expired'])
        ).limit(1)
    )
    members_sample = members_sample_result.scalar_one_or_none()
    tables_data.append(TableInfo(
        name="members",
        count=members_count,
        sample=member_to_sample(members_sample) if members_sample else None
    ))

    # Member Edges
    edges_count_result = await db.execute(
        select(func.count(MemberEdge.id)).where(MemberEdge.is_active == True)
    )
    edges_count = edges_count_result.scalar() or 0

    edges_sample_result = await db.execute(
        select(MemberEdge).where(MemberEdge.is_active == True).limit(1)
    )
    edges_sample = edges_sample_result.scalar_one_or_none()
    tables_data.append(TableInfo(
        name="member_edges",
        count=edges_count,
        sample=edge_to_sample(edges_sample) if edges_sample else None
    ))

    # Taste Profiles
    taste_count_result = await db.execute(
        select(func.count(TasteProfile.id))
    )
    taste_count = taste_count_result.scalar() or 0

    taste_sample_result = await db.execute(
        select(TasteProfile).limit(1)
    )
    taste_sample = taste_sample_result.scalar_one_or_none()
    tables_data.append(TableInfo(
        name="taste_profiles",
        count=taste_count,
        sample=taste_profile_to_sample(taste_sample) if taste_sample else None
    ))

    # Patterns
    patterns_count_result = await db.execute(
        select(func.count(Pattern.id)).where(Pattern.is_active == True)
    )
    patterns_count = patterns_count_result.scalar() or 0

    patterns_sample_result = await db.execute(
        select(Pattern).where(Pattern.is_active == True).limit(1)
    )
    patterns_sample = patterns_sample_result.scalar_one_or_none()
    tables_data.append(TableInfo(
        name="patterns",
        count=patterns_count,
        sample=pattern_to_sample(patterns_sample) if patterns_sample else None
    ))

    # Questions
    questions_count_result = await db.execute(
        select(func.count(Question.id)).where(Question.is_active == True)
    )
    questions_count = questions_count_result.scalar() or 0

    questions_sample_result = await db.execute(
        select(Question).where(Question.is_active == True).limit(1)
    )
    questions_sample = questions_sample_result.scalar_one_or_none()
    tables_data.append(TableInfo(
        name="questions",
        count=questions_count,
        sample=question_to_sample(questions_sample) if questions_sample else None
    ))

    # Question Deliveries
    deliveries_count_result = await db.execute(
        select(func.count(QuestionDelivery.id))
    )
    deliveries_count = deliveries_count_result.scalar() or 0

    deliveries_sample_result = await db.execute(
        select(QuestionDelivery).limit(1)
    )
    deliveries_sample = deliveries_sample_result.scalar_one_or_none()
    tables_data.append(TableInfo(
        name="question_deliveries",
        count=deliveries_count,
        sample=delivery_to_sample(deliveries_sample) if deliveries_sample else None
    ))

    # Event Signals
    signals_count_result = await db.execute(
        select(func.count(EventSignal.id))
    )
    signals_count = signals_count_result.scalar() or 0

    signals_sample_result = await db.execute(
        select(EventSignal).limit(1)
    )
    signals_sample = signals_sample_result.scalar_one_or_none()
    tables_data.append(TableInfo(
        name="event_signals",
        count=signals_count,
        sample=signal_to_sample(signals_sample) if signals_sample else None
    ))

    # Question Responses
    responses_count_result = await db.execute(
        select(func.count(QuestionResponse.id))
    )
    responses_count = responses_count_result.scalar() or 0

    responses_sample_result = await db.execute(
        select(QuestionResponse).limit(1)
    )
    responses_sample = responses_sample_result.scalar_one_or_none()
    tables_data.append(TableInfo(
        name="question_responses",
        count=responses_count,
        sample=response_to_sample(responses_sample) if responses_sample else None
    ))

    # Define relationships
    relationships = [
        Relationship(from_table="members", to_table="member_edges", type="1:N"),
        Relationship(from_table="members", to_table="taste_profiles", type="1:1"),
        Relationship(from_table="members", to_table="event_signals", type="1:N"),
        Relationship(from_table="members", to_table="question_deliveries", type="1:N"),
        Relationship(from_table="members", to_table="question_responses", type="1:N"),
        Relationship(from_table="patterns", to_table="member_edges", type="1:N"),
        Relationship(from_table="patterns", to_table="members", type="N:M"),
        Relationship(from_table="questions", to_table="question_deliveries", type="1:N"),
        Relationship(from_table="questions", to_table="question_responses", type="1:N"),
        Relationship(from_table="question_deliveries", to_table="question_responses", type="1:1"),
    ]

    response = ModelStatsResponse(
        tables=tables_data,
        relationships=relationships
    )

    # Cache the result
    _model_cache = (datetime.now(), response.model_dump())

    return response


@router.post("/cache/clear")
async def clear_stats_cache():
    """Clear the stats cache. Use after major data changes."""
    global _model_cache
    was_cached = _model_cache is not None
    _model_cache = None
    return {"message": "Model stats cache cleared" if was_cached else "Cache was already empty"}


@router.get("/activity", response_model=ActivityFeedResponse)
async def get_activity_feed(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent activity feed showing system events.

    Returns the most recent activities including edge discoveries,
    question answers, pattern updates, and taste profile changes.
    """
    activities: List[Activity] = []

    # Get member name lookup
    members_result = await db.execute(
        select(Member.id, Member.first_name, Member.last_name)
    )
    members_map = {
        row[0]: f"{row[1] or ''} {row[2] or ''}".strip() or f"Member {row[0]}"
        for row in members_result.all()
    }

    # Recent edges discovered
    edges_result = await db.execute(
        select(MemberEdge)
        .where(MemberEdge.is_active == True)
        .order_by(desc(MemberEdge.created_at))
        .limit(limit // 4)
    )
    for edge in edges_result.scalars().all():
        member_a_name = members_map.get(edge.member_a_id, f"Member {edge.member_a_id}")
        member_b_name = members_map.get(edge.member_b_id, f"Member {edge.member_b_id}")
        activities.append(Activity(
            type="edge_discovered",
            description=f"{member_a_name} <-> {member_b_name} ({edge.edge_type.value.replace('_', ' ')})",
            timestamp=edge.created_at
        ))

    # Recent question responses
    responses_result = await db.execute(
        select(QuestionResponse)
        .order_by(desc(QuestionResponse.created_at))
        .limit(limit // 4)
    )
    for response in responses_result.scalars().all():
        member_name = members_map.get(response.member_id, f"Member {response.member_id}")
        response_preview = response.response_text[:50] + "..." if len(response.response_text) > 50 else response.response_text
        activities.append(Activity(
            type="question_answered",
            description=f"{member_name} answered: \"{response_preview}\"",
            timestamp=response.created_at
        ))

    # Recent pattern updates
    patterns_result = await db.execute(
        select(Pattern)
        .where(Pattern.is_active == True)
        .order_by(desc(Pattern.updated_at))
        .limit(limit // 4)
    )
    for pattern in patterns_result.scalars().all():
        activities.append(Activity(
            type="pattern_updated",
            description=f"\"{pattern.name}\" now has {pattern.member_count} members",
            timestamp=pattern.updated_at
        ))

    # Recent taste profile updates
    taste_result = await db.execute(
        select(TasteProfile)
        .order_by(desc(TasteProfile.updated_at))
        .limit(limit // 4)
    )
    for taste in taste_result.scalars().all():
        member_name = members_map.get(taste.member_id, f"Member {taste.member_id}")
        if taste.vibe_words and taste.updated_at:
            vibes = ", ".join(taste.vibe_words[:2])
            activities.append(Activity(
                type="taste_evolved",
                description=f"{member_name} vibes with: {vibes}",
                timestamp=taste.updated_at
            ))

    # Sort all activities by timestamp descending, filtering out any None timestamps
    activities = [a for a in activities if a.timestamp is not None]
    activities.sort(key=lambda a: a.timestamp, reverse=True)

    return ActivityFeedResponse(
        activities=activities[:limit]
    )
