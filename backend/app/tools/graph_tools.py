"""Tools for graph operations and edge discovery between community members."""

import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models import Member, MemberEdge, Pattern, EdgeType

logger = logging.getLogger(__name__)


async def get_all_members_with_profiles(db: AsyncSession) -> dict[str, Any]:
    """
    Fetch all active members with their skills, interests, bio, and other profile data.

    Returns data structured for edge discovery analysis.
    """
    result = await db.execute(
        select(Member).where(Member.membership_status.notin_(['cancelled', 'expired']))
    )
    members = result.scalars().all()

    member_profiles = []
    for member in members:
        member_name = f"{member.first_name or ''} {member.last_name or ''}".strip()
        member_profiles.append({
            "id": member.id,
            "name": member_name or "Anonymous",
            "bio": member.bio,
            "role": member.role,
            "company": member.company,
            "location": member.location,
            "skills": member.skills or [],
            "interests": member.interests or [],
            "all_traits": member.all_traits or [],
        })

    return {
        "total_members": len(member_profiles),
        "members": member_profiles,
    }


async def get_existing_edges(db: AsyncSession) -> dict[str, Any]:
    """
    Get all existing edges to avoid creating duplicates.

    Returns edge pairs and their types for deduplication.
    """
    result = await db.execute(
        select(MemberEdge).where(MemberEdge.is_active == True)
    )
    edges = result.scalars().all()

    edge_list = []
    edge_pairs = set()  # Set of (min_id, max_id, type) tuples for quick lookup

    for edge in edges:
        # Normalize pair order for consistent lookup
        pair_key = (
            min(edge.member_a_id, edge.member_b_id),
            max(edge.member_a_id, edge.member_b_id),
            edge.edge_type.value
        )
        edge_pairs.add(pair_key)

        edge_list.append({
            "id": edge.id,
            "member_a_id": edge.member_a_id,
            "member_b_id": edge.member_b_id,
            "edge_type": edge.edge_type.value,
            "strength": edge.strength,
            "evidence": edge.evidence or {},
        })

    return {
        "total_edges": len(edge_list),
        "edges": edge_list,
        "existing_pairs": [list(p) for p in edge_pairs],  # JSON-serializable
    }


async def get_active_patterns(db: AsyncSession) -> dict[str, Any]:
    """
    Get active patterns that can serve as evidence for edges.

    Patterns like skill_cluster and interest_theme provide context
    for why two members might be connected.
    """
    result = await db.execute(
        select(Pattern).where(Pattern.is_active == True).order_by(Pattern.member_count.desc())
    )
    patterns = result.scalars().all()

    return {
        "total_patterns": len(patterns),
        "patterns": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "category": p.category.value,
                "member_count": p.member_count,
                "related_member_ids": p.related_member_ids or [],
                "evidence": p.evidence or {},
            }
            for p in patterns
        ],
    }


async def save_edge(db: AsyncSession, edge_data: dict[str, Any]) -> dict[str, Any]:
    """
    Create a new MemberEdge record.

    Args:
        db: Database session.
        edge_data: Edge data including member_a_id, member_b_id, edge_type, strength, evidence.

    Returns:
        dict with edge id, status, and whether it was created or already existed.
    """
    member_a_id = edge_data.get("member_a_id")
    member_b_id = edge_data.get("member_b_id")
    edge_type_str = edge_data.get("edge_type")
    strength = edge_data.get("strength", 50)
    evidence = edge_data.get("evidence", {})
    discovered_via = edge_data.get("discovered_via", "edge_discovery_agent")

    # Validation
    if not member_a_id or not member_b_id:
        return {"error": "Both member_a_id and member_b_id are required"}

    if member_a_id == member_b_id:
        return {"error": "Cannot create edge between a member and themselves"}

    if not edge_type_str:
        return {"error": "edge_type is required"}

    # Convert edge_type string to enum
    try:
        edge_type = EdgeType(edge_type_str)
    except ValueError:
        valid_types = [t.value for t in EdgeType]
        return {"error": f"Invalid edge_type: {edge_type_str}. Valid types: {valid_types}"}

    # Validate strength
    if not (0 <= strength <= 100):
        return {"error": "strength must be between 0 and 100"}

    # Normalize member order to prevent duplicate edges (A-B vs B-A)
    normalized_a = min(member_a_id, member_b_id)
    normalized_b = max(member_a_id, member_b_id)

    # Check for existing edge of the same type
    result = await db.execute(
        select(MemberEdge).where(
            and_(
                MemberEdge.member_a_id == normalized_a,
                MemberEdge.member_b_id == normalized_b,
                MemberEdge.edge_type == edge_type,
                MemberEdge.is_active == True
            )
        )
    )
    existing_edge = result.scalar_one_or_none()

    if existing_edge:
        # Update existing edge if new strength is higher
        if strength > existing_edge.strength:
            existing_edge.strength = strength
            # Merge evidence
            existing_evidence = existing_edge.evidence or {}
            if evidence:
                for key, value in evidence.items():
                    if key in existing_evidence and isinstance(existing_evidence[key], list) and isinstance(value, list):
                        existing_evidence[key] = list(set(existing_evidence[key] + value))
                    else:
                        existing_evidence[key] = value
                existing_edge.evidence = existing_evidence
            await db.commit()
            await db.refresh(existing_edge)
            logger.info(f"Updated existing edge {existing_edge.id} with higher strength: {strength}")
            return {
                "id": existing_edge.id,
                "status": "updated",
                "strength": existing_edge.strength,
                "message": f"Edge already existed, updated strength to {strength}",
            }
        else:
            logger.debug(f"Edge already exists with equal or higher strength: {existing_edge.id}")
            return {
                "id": existing_edge.id,
                "status": "already_exists",
                "strength": existing_edge.strength,
                "message": "Edge already exists with equal or higher strength",
            }

    # Create new edge
    new_edge = MemberEdge(
        member_a_id=normalized_a,
        member_b_id=normalized_b,
        edge_type=edge_type,
        strength=strength,
        discovered_via=discovered_via,
        evidence=evidence,
        is_active=True,
    )
    db.add(new_edge)
    await db.commit()
    await db.refresh(new_edge)

    logger.info(f"Created new edge {new_edge.id}: {normalized_a} <-> {normalized_b} ({edge_type.value})")

    return {
        "id": new_edge.id,
        "status": "created",
        "member_a_id": new_edge.member_a_id,
        "member_b_id": new_edge.member_b_id,
        "edge_type": new_edge.edge_type.value,
        "strength": new_edge.strength,
    }


# Tool definitions for Claude API

GET_ALL_MEMBERS_TOOL = {
    "name": "get_all_members_with_profiles",
    "description": """Fetch all active community members with their profile data for edge discovery.

Returns for each member:
- id: Unique member ID (use this for edge creation)
- name: Member's display name
- bio: Member's biography/description
- role: Professional role or title
- company: Company or organization
- location: Geographic location
- skills: Array of skills
- interests: Array of interests
- all_traits: Combined traits from various sources

Use this data to identify potential connections between members based on overlapping skills, interests, complementary abilities, or shared context (location, industry, etc.).""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


GET_EXISTING_EDGES_TOOL = {
    "name": "get_existing_edges",
    "description": """Get all existing edges in the community graph.

Returns:
- total_edges: Count of active edges
- edges: Array of edge objects with member IDs, type, strength, and evidence
- existing_pairs: Array of [member_a_id, member_b_id, edge_type] for quick duplicate checking

Use this to avoid creating duplicate edges. Before saving an edge, check if the pair already exists.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


GET_ACTIVE_PATTERNS_TOOL = {
    "name": "get_active_patterns",
    "description": """Get active community patterns that can serve as edge evidence.

Patterns provide context for why members might be connected:
- skill_cluster: Shared technical or creative abilities
- interest_theme: Common passions or curiosities
- collaboration_opportunity: Complementary skills for partnership
- community_strength: Core competencies of the community
- cross_domain: Interesting overlaps between different areas

Use pattern membership to create pattern_connection edges between members who share the same pattern.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


SAVE_EDGE_TOOL = {
    "name": "save_edge",
    "description": """Create a new edge (connection) between two community members.

Edge Types:
- shared_skill: Both members have the same skill(s)
- shared_interest: Both members share an interest
- collaboration_potential: Complementary skills that could work together
- pattern_connection: Both members are part of the same discovered pattern

Strength Guidelines (0-100):
- 90-100: Strong connection (3+ shared items, or deep complementary fit)
- 70-89: Moderate connection (2 shared items, good potential)
- 50-69: Light connection (1 shared item, some overlap)
- Below 50: Weak (usually not worth creating)

Evidence should include the specific items creating the connection (skill names, interest names, pattern IDs, etc.).""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_a_id": {
                "type": "integer",
                "description": "ID of the first member"
            },
            "member_b_id": {
                "type": "integer",
                "description": "ID of the second member"
            },
            "edge_type": {
                "type": "string",
                "enum": ["shared_skill", "shared_interest", "collaboration_potential", "event_co_attendance", "introduced_by_agent", "pattern_connection"],
                "description": "Type of connection between members"
            },
            "strength": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Connection strength (0-100). Higher = stronger connection."
            },
            "evidence": {
                "type": "object",
                "description": "Evidence for this connection. Include: shared_skills, shared_interests, pattern_ids, notes, reasoning",
                "properties": {
                    "shared_skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Skills that both members share"
                    },
                    "shared_interests": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Interests that both members share"
                    },
                    "pattern_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Pattern IDs that connect these members"
                    },
                    "pattern_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of patterns that connect these members"
                    },
                    "complementary_skills": {
                        "type": "object",
                        "description": "For collaboration_potential: {member_a_brings: [...], member_b_brings: [...]}"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional context about why this connection matters"
                    }
                }
            },
            "discovered_via": {
                "type": "string",
                "description": "How this edge was discovered (default: edge_discovery_agent)"
            }
        },
        "required": ["member_a_id", "member_b_id", "edge_type", "strength", "evidence"]
    }
}
