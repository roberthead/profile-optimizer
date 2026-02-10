"""Tools for GroupQuestionAgent to work with groups of members."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Member,
    Question,
    QuestionDelivery,
    MemberEdge,
    TasteProfile,
    Pattern,
    DeliveryStatus,
    QuestionVibe,
)

logger = logging.getLogger(__name__)


async def get_present_member_profiles(
    db: AsyncSession,
    member_ids: list[int],
) -> list[dict[str, Any]]:
    """
    Get full profiles for a group of present members.

    Returns comprehensive profile data including:
    - Basic profile info (name, bio, role, company)
    - Skills and interests
    - Patterns they belong to
    - Edges to other members
    - Taste preferences

    Args:
        db: Database session
        member_ids: List of member IDs who are present

    Returns:
        List of member profile dictionaries
    """
    if not member_ids:
        return []

    logger.info(f"Fetching profiles for {len(member_ids)} present members")

    # Get members
    result = await db.execute(
        select(Member).where(Member.id.in_(member_ids))
    )
    members = result.scalars().all()

    # Get taste profiles for all members
    taste_result = await db.execute(
        select(TasteProfile).where(TasteProfile.member_id.in_(member_ids))
    )
    taste_profiles = {tp.member_id: tp for tp in taste_result.scalars().all()}

    # Get patterns that include any of these members
    pattern_result = await db.execute(
        select(Pattern).where(
            and_(
                Pattern.is_active == True,
                # Check if any member_id is in the pattern's related_member_ids
                or_(*[
                    Pattern.related_member_ids.contains([mid])
                    for mid in member_ids
                ])
            )
        )
    )
    patterns = pattern_result.scalars().all()

    # Build pattern lookup by member
    member_patterns: dict[int, list[dict]] = {mid: [] for mid in member_ids}
    for pattern in patterns:
        for mid in member_ids:
            if pattern.related_member_ids and mid in pattern.related_member_ids:
                member_patterns[mid].append({
                    "id": pattern.id,
                    "name": pattern.name,
                    "category": pattern.category.value,
                    "description": pattern.description,
                })

    # Build profiles
    profiles = []
    for member in members:
        member_name = f"{member.first_name or ''} {member.last_name or ''}".strip()
        taste = taste_profiles.get(member.id)

        profile = {
            "member_id": member.id,
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
            "patterns": member_patterns.get(member.id, []),
            "taste_profile": None,
        }

        if taste:
            profile["taste_profile"] = {
                "vibe_words": taste.vibe_words or [],
                "avoid_words": taste.avoid_words or [],
                "energy_time": taste.energy_time,
                "usual_company": taste.usual_company,
                "spontaneity": taste.spontaneity,
                "dealbreakers": taste.dealbreakers or [],
                "current_mood": taste.current_mood,
                "this_week_energy": taste.this_week_energy,
            }

        profiles.append(profile)

    return profiles


async def get_group_edges(
    db: AsyncSession,
    member_ids: list[int],
) -> list[dict[str, Any]]:
    """
    Get all edges (connections) between the specified group of members.

    Returns edges where both endpoints are in the group, useful for
    understanding existing relationships and connection strengths.

    Args:
        db: Database session
        member_ids: List of member IDs in the group

    Returns:
        List of edge dictionaries with member names and edge metadata
    """
    if len(member_ids) < 2:
        return []

    logger.info(f"Fetching edges between {len(member_ids)} members")

    # Get edges where both members are in our group
    result = await db.execute(
        select(MemberEdge).where(
            and_(
                MemberEdge.is_active == True,
                MemberEdge.member_a_id.in_(member_ids),
                MemberEdge.member_b_id.in_(member_ids),
            )
        )
    )
    edges = result.scalars().all()

    # Get member names for context
    members_result = await db.execute(
        select(Member).where(Member.id.in_(member_ids))
    )
    member_names = {}
    for m in members_result.scalars().all():
        name = f"{m.first_name or ''} {m.last_name or ''}".strip()
        member_names[m.id] = name or "Anonymous"

    edge_list = []
    for edge in edges:
        edge_list.append({
            "edge_id": edge.id,
            "member_a_id": edge.member_a_id,
            "member_a_name": member_names.get(edge.member_a_id, "Unknown"),
            "member_b_id": edge.member_b_id,
            "member_b_name": member_names.get(edge.member_b_id, "Unknown"),
            "edge_type": edge.edge_type.value,
            "strength": edge.strength,
            "discovered_via": edge.discovered_via,
            "evidence": edge.evidence or {},
        })

    return edge_list


async def get_recent_group_questions(
    db: AsyncSession,
    member_ids: list[int],
    days: int = 7,
) -> list[int]:
    """
    Get question IDs that have been asked to groups including these members recently.

    Helps avoid repeating questions that the group has already seen together.
    Returns question IDs that were delivered to ANY of the specified members
    within the time window.

    Args:
        db: Database session
        member_ids: List of member IDs in the current group
        days: Number of days to look back (default 7)

    Returns:
        List of question IDs to potentially avoid
    """
    if not member_ids:
        return []

    logger.info(f"Checking recent questions for {len(member_ids)} members over {days} days")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get questions delivered to any of these members recently
    result = await db.execute(
        select(QuestionDelivery.question_id).where(
            and_(
                QuestionDelivery.member_id.in_(member_ids),
                QuestionDelivery.created_at >= cutoff,
                QuestionDelivery.delivery_status.in_([
                    DeliveryStatus.DELIVERED,
                    DeliveryStatus.VIEWED,
                    DeliveryStatus.ANSWERED,
                ])
            )
        ).distinct()
    )

    question_ids = [row[0] for row in result.fetchall()]

    logger.info(f"Found {len(question_ids)} recently asked questions")
    return question_ids


def score_question_for_group(
    question: dict[str, Any],
    members: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> float:
    """
    Score how well a question fits a specific group of members.

    Scoring considers:
    - Skill/interest overlap with question targeting
    - Edge relevance (questions about connections present in the group)
    - Pattern matching (questions about patterns the group shares)
    - Vibe compatibility with group taste profiles
    - Difficulty appropriateness for group size

    Args:
        question: Question dict with targeting metadata
        members: List of member profile dicts from get_present_member_profiles
        edges: List of edge dicts from get_group_edges

    Returns:
        Score from 0-100 indicating question fit for the group
    """
    score = 50.0  # Base score

    if not members:
        return 0.0

    group_size = len(members)
    member_ids = {m["member_id"] for m in members}

    # 1. Check if question is specifically about members in the group
    relevant_member_ids = set(question.get("relevant_member_ids") or [])
    if relevant_member_ids:
        overlap = relevant_member_ids & member_ids
        if overlap:
            # Strong boost if question is about people in the room
            score += 20 * (len(overlap) / len(relevant_member_ids))

    # 2. Check edge context relevance
    edge_context = question.get("edge_context") or {}
    if edge_context:
        # Check if the edge mentioned is between members in the group
        edge_member_ids = set()
        if "member_a_id" in edge_context:
            edge_member_ids.add(edge_context["member_a_id"])
        if "member_b_id" in edge_context:
            edge_member_ids.add(edge_context["member_b_id"])

        if edge_member_ids and edge_member_ids <= member_ids:
            score += 15  # Both edge members are present

    # 3. Skill/interest matching
    targeting = question.get("targeting_criteria") or {}
    target_skills = set(targeting.get("skill_match") or [])
    target_interests = set(targeting.get("interest_match") or [])

    group_skills = set()
    group_interests = set()
    for m in members:
        profile = m.get("profile") or {}
        group_skills.update(profile.get("skills") or [])
        group_interests.update(profile.get("interests") or [])

    if target_skills and group_skills:
        skill_overlap = len(target_skills & group_skills) / len(target_skills)
        score += 10 * skill_overlap

    if target_interests and group_interests:
        interest_overlap = len(target_interests & group_interests) / len(target_interests)
        score += 10 * interest_overlap

    # 4. Pattern matching
    target_patterns = set(targeting.get("pattern_ids") or [])
    if target_patterns:
        group_patterns = set()
        for m in members:
            for p in m.get("patterns") or []:
                group_patterns.add(p["id"])

        if group_patterns:
            pattern_overlap = len(target_patterns & group_patterns) / len(target_patterns)
            score += 15 * pattern_overlap

    # 5. Vibe compatibility
    question_vibe = question.get("vibe")
    if question_vibe:
        # Count how many members have compatible vibes
        vibe_compatible = 0
        for m in members:
            taste = m.get("taste_profile") or {}
            vibe_words = taste.get("vibe_words") or []
            avoid_words = taste.get("avoid_words") or []

            # Simple vibe word matching
            vibe_map = {
                "warm": ["cozy", "friendly", "welcoming", "warm"],
                "playful": ["fun", "playful", "silly", "light"],
                "deep": ["deep", "thoughtful", "meaningful", "introspective"],
                "edgy": ["edgy", "provocative", "bold", "challenging"],
                "connector": ["social", "connecting", "networking", "community"],
            }

            compatible_words = vibe_map.get(question_vibe, [])
            if any(word in vibe_words for word in compatible_words):
                vibe_compatible += 1
            elif any(word in avoid_words for word in compatible_words):
                vibe_compatible -= 1

        if group_size > 0:
            vibe_score = vibe_compatible / group_size
            score += 10 * vibe_score

    # 6. Difficulty vs group size adjustment
    difficulty = question.get("difficulty_level", 1)
    if group_size >= 4 and difficulty == 1:
        # Easy questions work well for larger groups
        score += 5
    elif group_size <= 2 and difficulty == 3:
        # Deep questions work better for smaller groups
        score += 5
    elif group_size >= 5 and difficulty == 3:
        # Deep questions may be awkward in very large groups
        score -= 5

    # 7. Category distribution (boost underrepresented categories)
    # This could be enhanced by tracking what categories have been asked

    # 8. Connector vibe bonus for groups with many edges
    if edges and question_vibe == "connector":
        edge_density = len(edges) / (group_size * (group_size - 1) / 2) if group_size > 1 else 0
        if edge_density > 0.5:
            score += 10  # Well-connected group benefits from connector questions

    # Ensure score is in valid range
    return max(0.0, min(100.0, score))


# Tool definitions for Claude API

GET_PRESENT_MEMBER_PROFILES_TOOL = {
    "name": "get_present_member_profiles",
    "description": """Get full profiles for a group of members who are present together.

Returns comprehensive data for each member:
- Profile: name, bio, role, company, skills, interests, traits
- Patterns: community patterns they belong to (skill clusters, interest themes, etc.)
- Taste profile: vibe words, avoid words, energy preferences, mood

Use this to understand who is in the group and find conversation starters,
shared interests, or complementary skills to explore.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of member IDs who are present in the group"
            }
        },
        "required": ["member_ids"]
    }
}


GET_GROUP_EDGES_TOOL = {
    "name": "get_group_edges",
    "description": """Get all connections (edges) between members in a group.

Returns edges with:
- member_a_id/name and member_b_id/name
- edge_type: shared_skill, shared_interest, collaboration_potential, pattern_connection
- strength: 0-100 connection strength
- evidence: Why this connection exists

Use this to understand existing relationships within the group and find
questions that can strengthen or explore these connections.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of member IDs in the group"
            }
        },
        "required": ["member_ids"]
    }
}


GET_RECENT_GROUP_QUESTIONS_TOOL = {
    "name": "get_recent_group_questions",
    "description": """Get question IDs recently asked to members in this group.

Returns question IDs that were delivered to ANY member in the group
within the specified time window. Use this to avoid repeating questions
the group may have already discussed.

Default lookback is 7 days.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of member IDs in the current group"
            },
            "days": {
                "type": "integer",
                "description": "Number of days to look back (default: 7)"
            }
        },
        "required": ["member_ids"]
    }
}


SCORE_QUESTION_FOR_GROUP_TOOL = {
    "name": "score_question_for_group",
    "description": """Score how well a question fits a specific group of members.

Scoring considers:
- Relevance: Is the question about people in the group?
- Edge context: Does it reference connections between present members?
- Skill/interest match: Does targeting align with group expertise?
- Pattern matching: Does it relate to patterns the group shares?
- Vibe compatibility: Does question tone match group preferences?
- Group size: Is difficulty appropriate for the number of people?

Returns a score from 0-100.

Note: This is a local scoring function. Call it after retrieving
member profiles and edges from the database tools.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "object",
                "description": "Question dict with id, question_text, category, vibe, relevant_member_ids, edge_context, targeting_criteria, difficulty_level"
            },
            "members": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of member profile dicts from get_present_member_profiles"
            },
            "edges": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of edge dicts from get_group_edges"
            }
        },
        "required": ["question", "members", "edges"]
    }
}
