"""Tools for question targeting and member-question matching."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc

from app.models import (
    Member,
    Question,
    QuestionDelivery,
    QuestionResponse,
    MemberEdge,
    TasteProfile,
    Pattern,
    DeliveryChannel,
    DeliveryStatus,
    QuestionVibe,
)

logger = logging.getLogger(__name__)


async def get_question_pool(
    db: AsyncSession,
    member_id: int,
    channel: Optional[DeliveryChannel] = None,
    include_answered: bool = False,
) -> dict[str, Any]:
    """
    Get available questions that haven't been asked to a specific member.

    Filters out questions already delivered (unless include_answered=True).
    Optionally filters by channel suitability.

    Returns questions with their targeting metadata.
    """
    # Get questions already delivered to this member
    delivered_query = select(QuestionDelivery.question_id).where(
        and_(
            QuestionDelivery.member_id == member_id,
            QuestionDelivery.delivery_status.in_([
                DeliveryStatus.DELIVERED,
                DeliveryStatus.VIEWED,
                DeliveryStatus.ANSWERED,
            ])
        )
    )
    delivered_result = await db.execute(delivered_query)
    delivered_question_ids = {row[0] for row in delivered_result.fetchall()}

    # Also check QuestionResponse for answered questions
    answered_query = select(QuestionResponse.question_id).where(
        QuestionResponse.member_id == member_id
    )
    answered_result = await db.execute(answered_query)
    answered_question_ids = {row[0] for row in answered_result.fetchall()}

    excluded_ids = delivered_question_ids | answered_question_ids

    # Build question query
    query = select(Question).where(Question.is_active == True)

    if not include_answered and excluded_ids:
        query = query.where(Question.id.notin_(excluded_ids))

    result = await db.execute(query.order_by(Question.created_at.desc()))
    questions = result.scalars().all()

    question_list = []
    for q in questions:
        question_data = {
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
            "deck_id": q.deck_id,
        }
        question_list.append(question_data)

    return {
        "total_available": len(question_list),
        "excluded_count": len(excluded_ids),
        "questions": question_list,
    }


async def get_member_context(
    db: AsyncSession,
    member_id: int,
) -> dict[str, Any]:
    """
    Get comprehensive context about a member for targeting decisions.

    Includes profile data, taste profile, recent activity, and engagement patterns.
    """
    # Get member profile
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()

    if not member:
        return {"error": f"Member {member_id} not found"}

    # Get taste profile
    taste_result = await db.execute(
        select(TasteProfile).where(TasteProfile.member_id == member_id)
    )
    taste_profile = taste_result.scalar_one_or_none()

    # Get recent question activity (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    recent_deliveries = await db.execute(
        select(QuestionDelivery)
        .where(
            and_(
                QuestionDelivery.member_id == member_id,
                QuestionDelivery.created_at >= thirty_days_ago
            )
        )
        .order_by(desc(QuestionDelivery.created_at))
        .limit(20)
    )
    deliveries = recent_deliveries.scalars().all()

    # Calculate engagement metrics
    total_delivered = len(deliveries)
    answered = sum(1 for d in deliveries if d.delivery_status == DeliveryStatus.ANSWERED)
    skipped = sum(1 for d in deliveries if d.delivery_status == DeliveryStatus.SKIPPED)

    # Get last question timestamp
    last_question_at = None
    if deliveries:
        last_question_at = deliveries[0].created_at.isoformat()

    # Get patterns this member belongs to
    pattern_result = await db.execute(
        select(Pattern).where(
            and_(
                Pattern.is_active == True,
                Pattern.related_member_ids.contains([member_id])
            )
        )
    )
    member_patterns = pattern_result.scalars().all()

    member_name = f"{member.first_name or ''} {member.last_name or ''}".strip()

    context = {
        "member_id": member_id,
        "name": member_name or "Anonymous",
        "profile": {
            "bio": member.bio,
            "role": member.role,
            "company": member.company,
            "location": member.location,
            "skills": member.skills or [],
            "interests": member.interests or [],
            "all_traits": member.all_traits or [],
        },
        "taste_profile": None,
        "engagement": {
            "questions_received_30d": total_delivered,
            "questions_answered_30d": answered,
            "questions_skipped_30d": skipped,
            "answer_rate": round(answered / total_delivered * 100, 1) if total_delivered > 0 else None,
            "last_question_at": last_question_at,
        },
        "patterns": [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category.value,
            }
            for p in member_patterns
        ],
    }

    if taste_profile:
        context["taste_profile"] = {
            "vibe_words": taste_profile.vibe_words or [],
            "avoid_words": taste_profile.avoid_words or [],
            "energy_time": taste_profile.energy_time,
            "usual_company": taste_profile.usual_company,
            "spontaneity": taste_profile.spontaneity,
            "dealbreakers": taste_profile.dealbreakers or [],
            "current_mood": taste_profile.current_mood,
            "this_week_energy": taste_profile.this_week_energy,
        }

    return context


async def get_member_edges(
    db: AsyncSession,
    member_id: int,
) -> dict[str, Any]:
    """
    Get all edges (connections) for a member.

    Returns edges with connected member details and edge metadata.
    """
    # Get edges where member is either member_a or member_b
    result = await db.execute(
        select(MemberEdge).where(
            and_(
                MemberEdge.is_active == True,
                or_(
                    MemberEdge.member_a_id == member_id,
                    MemberEdge.member_b_id == member_id
                )
            )
        )
    )
    edges = result.scalars().all()

    # Get connected member IDs
    connected_ids = set()
    for edge in edges:
        if edge.member_a_id == member_id:
            connected_ids.add(edge.member_b_id)
        else:
            connected_ids.add(edge.member_a_id)

    # Get connected member names
    member_names = {}
    if connected_ids:
        members_result = await db.execute(
            select(Member).where(Member.id.in_(connected_ids))
        )
        for m in members_result.scalars().all():
            name = f"{m.first_name or ''} {m.last_name or ''}".strip()
            member_names[m.id] = name or "Anonymous"

    edge_list = []
    for edge in edges:
        connected_id = edge.member_b_id if edge.member_a_id == member_id else edge.member_a_id
        edge_list.append({
            "edge_id": edge.id,
            "connected_member_id": connected_id,
            "connected_member_name": member_names.get(connected_id, "Unknown"),
            "edge_type": edge.edge_type.value,
            "strength": edge.strength,
            "evidence": edge.evidence or {},
        })

    return {
        "member_id": member_id,
        "total_connections": len(edge_list),
        "edges": edge_list,
    }


async def get_answered_questions(
    db: AsyncSession,
    member_id: int,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Get questions that a member has already answered.

    Includes the question category and vibe for similarity detection.
    """
    # Get from QuestionResponse
    response_result = await db.execute(
        select(QuestionResponse, Question)
        .join(Question, QuestionResponse.question_id == Question.id)
        .where(QuestionResponse.member_id == member_id)
        .order_by(desc(QuestionResponse.created_at))
        .limit(limit)
    )
    responses = response_result.fetchall()

    # Get from QuestionDelivery with ANSWERED status
    delivery_result = await db.execute(
        select(QuestionDelivery, Question)
        .join(Question, QuestionDelivery.question_id == Question.id)
        .where(
            and_(
                QuestionDelivery.member_id == member_id,
                QuestionDelivery.delivery_status == DeliveryStatus.ANSWERED
            )
        )
        .order_by(desc(QuestionDelivery.answered_at))
        .limit(limit)
    )
    deliveries = delivery_result.fetchall()

    answered = []
    seen_question_ids = set()

    # Process responses
    for response, question in responses:
        if question.id not in seen_question_ids:
            seen_question_ids.add(question.id)
            answered.append({
                "question_id": question.id,
                "question_text": question.question_text,
                "category": question.category.value,
                "vibe": question.vibe.value if question.vibe else None,
                "answered_at": response.created_at.isoformat(),
                "response_preview": response.response_text[:100] if response.response_text else None,
            })

    # Process deliveries (if not already in responses)
    for delivery, question in deliveries:
        if question.id not in seen_question_ids:
            seen_question_ids.add(question.id)
            answered.append({
                "question_id": question.id,
                "question_text": question.question_text,
                "category": question.category.value,
                "vibe": question.vibe.value if question.vibe else None,
                "answered_at": delivery.answered_at.isoformat() if delivery.answered_at else None,
                "response_preview": delivery.response_value[:100] if delivery.response_value else None,
            })

    # Sort by answered_at descending
    answered.sort(key=lambda x: x["answered_at"] or "", reverse=True)

    # Calculate category distribution
    category_counts = {}
    for a in answered:
        cat = a["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "member_id": member_id,
        "total_answered": len(answered),
        "category_distribution": category_counts,
        "answered_questions": answered[:limit],
    }


async def assign_question_to_member(
    db: AsyncSession,
    question_id: int,
    member_id: int,
    channel: DeliveryChannel,
    targeting_context: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Create a QuestionDelivery record to assign a question to a member.

    This tracks that the question was targeted to this member via this channel.
    """
    # Verify question exists
    question_result = await db.execute(
        select(Question).where(Question.id == question_id)
    )
    question = question_result.scalar_one_or_none()
    if not question:
        return {"error": f"Question {question_id} not found"}

    # Verify member exists
    member_result = await db.execute(
        select(Member).where(Member.id == member_id)
    )
    member = member_result.scalar_one_or_none()
    if not member:
        return {"error": f"Member {member_id} not found"}

    # Check if already delivered via this channel
    existing = await db.execute(
        select(QuestionDelivery).where(
            and_(
                QuestionDelivery.question_id == question_id,
                QuestionDelivery.member_id == member_id,
                QuestionDelivery.channel == channel,
            )
        )
    )
    if existing.scalar_one_or_none():
        return {
            "error": f"Question {question_id} already delivered to member {member_id} via {channel.value}",
            "already_exists": True,
        }

    # Create delivery record
    delivery = QuestionDelivery(
        question_id=question_id,
        member_id=member_id,
        channel=channel,
        delivery_status=DeliveryStatus.PENDING,
        targeting_context=targeting_context or {},
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)

    logger.info(
        f"Assigned question {question_id} to member {member_id} via {channel.value}"
    )

    return {
        "delivery_id": delivery.id,
        "question_id": question_id,
        "member_id": member_id,
        "channel": channel.value,
        "status": "created",
        "targeting_context": targeting_context,
    }


async def get_all_members_for_targeting(
    db: AsyncSession,
    active_only: bool = True,
) -> dict[str, Any]:
    """
    Get all members suitable for question targeting.

    Returns basic info and recent activity for each member.
    """
    query = select(Member)
    if active_only:
        query = query.where(Member.membership_status.notin_(['cancelled', 'expired']))

    result = await db.execute(query)
    members = result.scalars().all()

    # Get recent delivery counts for each member
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    member_list = []
    for member in members:
        # Get recent question count
        delivery_count = await db.execute(
            select(func.count(QuestionDelivery.id)).where(
                and_(
                    QuestionDelivery.member_id == member.id,
                    QuestionDelivery.created_at >= week_ago
                )
            )
        )
        recent_questions = delivery_count.scalar() or 0

        member_name = f"{member.first_name or ''} {member.last_name or ''}".strip()
        member_list.append({
            "id": member.id,
            "name": member_name or "Anonymous",
            "skills": member.skills or [],
            "interests": member.interests or [],
            "questions_this_week": recent_questions,
        })

    return {
        "total_members": len(member_list),
        "members": member_list,
    }


# Tool definitions for Claude API

GET_QUESTION_POOL_TOOL = {
    "name": "get_question_pool",
    "description": """Get available questions that haven't been asked to a specific member.

Returns questions with their targeting metadata including:
- question_id, question_text, category, difficulty_level
- vibe: The tone/energy of the question (warm, playful, deep, edgy, connector)
- relevant_member_ids: Members this question is specifically about
- edge_context: Information about member connections related to this question
- targeting_criteria: Pattern IDs, skill matches, etc.

Use this to understand what questions are available for a member.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The member to get available questions for"
            },
            "channel": {
                "type": "string",
                "enum": ["mobile_swipe", "clubhouse_display", "email", "sms", "web_chat"],
                "description": "Optional: Filter by channel suitability"
            },
            "include_answered": {
                "type": "boolean",
                "description": "Include questions already answered (default: false)"
            }
        },
        "required": ["member_id"]
    }
}


GET_MEMBER_CONTEXT_TOOL = {
    "name": "get_member_context",
    "description": """Get comprehensive context about a member for targeting decisions.

Returns:
- Profile: bio, role, skills, interests, traits
- Taste profile: vibe_words, avoid_words, energy preferences, mood
- Engagement: questions received/answered in last 30 days, answer rate
- Patterns: which community patterns this member belongs to

Use this to understand a member's preferences and energy level for question selection.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The member to get context for"
            }
        },
        "required": ["member_id"]
    }
}


GET_MEMBER_EDGES_TOOL = {
    "name": "get_member_edges",
    "description": """Get all connections (edges) for a member in the community graph.

Returns edges with:
- connected_member_id and name
- edge_type: shared_skill, shared_interest, collaboration_potential, pattern_connection
- strength: 0-100 connection strength
- evidence: Why this connection exists

Use this to find questions that involve members they're connected to.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The member to get edges for"
            }
        },
        "required": ["member_id"]
    }
}


GET_ANSWERED_QUESTIONS_TOOL = {
    "name": "get_answered_questions",
    "description": """Get questions a member has already answered.

Returns:
- List of answered questions with category, vibe, and response preview
- Category distribution to see which areas are well-covered
- Answered timestamps to avoid asking similar questions too soon

Use this to avoid repetitive questions and identify under-explored categories.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The member to check"
            },
            "limit": {
                "type": "integer",
                "description": "Max questions to return (default: 50)"
            }
        },
        "required": ["member_id"]
    }
}


ASSIGN_QUESTION_TO_MEMBER_TOOL = {
    "name": "assign_question_to_member",
    "description": """Create a QuestionDelivery record to assign a question to a member.

Creates a delivery record with:
- PENDING status
- The specified channel
- Targeting context explaining why this question was selected

Call this after scoring and selecting the best question(s) for a member.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "question_id": {
                "type": "integer",
                "description": "The question to assign"
            },
            "member_id": {
                "type": "integer",
                "description": "The member to receive the question"
            },
            "channel": {
                "type": "string",
                "enum": ["mobile_swipe", "clubhouse_display", "email", "sms", "web_chat"],
                "description": "Delivery channel for this question"
            },
            "targeting_context": {
                "type": "object",
                "description": "Why this question was selected (pattern_id, edge_id, relevance_score, selection_method, etc.)",
                "properties": {
                    "relevance_score": {"type": "integer", "description": "0-100 score"},
                    "selection_method": {"type": "string", "description": "highest_score, top_5_random, wildcard"},
                    "pattern_ids": {"type": "array", "items": {"type": "integer"}},
                    "edge_ids": {"type": "array", "items": {"type": "integer"}},
                    "vibe_match": {"type": "boolean"},
                    "reasoning": {"type": "string"}
                }
            }
        },
        "required": ["question_id", "member_id", "channel"]
    }
}


GET_ALL_MEMBERS_FOR_TARGETING_TOOL = {
    "name": "get_all_members_for_targeting",
    "description": """Get all members suitable for question targeting.

Returns for each member:
- id, name, skills, interests
- questions_this_week: How many questions they've received recently

Use this to find the best members for a specific question or for community-wide targeting.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "active_only": {
                "type": "boolean",
                "description": "Only include active members (default: true)"
            }
        },
        "required": []
    }
}
