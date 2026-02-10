"""Graph visualization API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
import hashlib
import json

from app.core.database import get_db
from app.models import Member, Pattern, MemberEdge, PatternCategory, EdgeType

router = APIRouter(prefix="/graph", tags=["graph"])

# Simple in-memory cache for graph data
_graph_cache: dict[str, Tuple[datetime, dict]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_cache_key(pattern_id: Optional[int], edge_types: Optional[List[str]]) -> str:
    """Generate a cache key from query parameters."""
    key_data = {
        "pattern_id": pattern_id,
        "edge_types": sorted(edge_types) if edge_types else None,
    }
    return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()


def _get_cached(key: str) -> Optional[dict]:
    """Get cached data if not expired."""
    if key in _graph_cache:
        cached_time, data = _graph_cache[key]
        if datetime.now() - cached_time < timedelta(seconds=CACHE_TTL_SECONDS):
            return data
        # Expired, remove from cache
        del _graph_cache[key]
    return None


def _set_cache(key: str, data: dict) -> None:
    """Store data in cache."""
    _graph_cache[key] = (datetime.now(), data)
    # Simple cleanup: remove old entries if cache gets too big
    if len(_graph_cache) > 100:
        now = datetime.now()
        expired_keys = [
            k for k, (t, _) in _graph_cache.items()
            if now - t >= timedelta(seconds=CACHE_TTL_SECONDS)
        ]
        for k in expired_keys:
            del _graph_cache[k]


class GraphNode(BaseModel):
    """A node in the graph representing a member."""
    id: int
    name: str
    photo_url: Optional[str]
    pattern_ids: List[int]
    connection_count: int
    skills: List[str]
    interests: List[str]
    role: Optional[str]
    company: Optional[str]
    bio: Optional[str]
    membership_status: str


class GraphEdge(BaseModel):
    """An edge in the graph representing a connection between members."""
    id: int
    source: int
    target: int
    type: str
    strength: int
    evidence: Optional[dict]
    discovered_via: str


class GraphPattern(BaseModel):
    """A pattern that groups members together."""
    id: int
    name: str
    description: str
    color: str
    member_ids: List[int]
    category: str


class GraphDataResponse(BaseModel):
    """Complete graph data for visualization."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    patterns: List[GraphPattern]


# Pattern category to color mapping
PATTERN_COLORS = {
    PatternCategory.SKILL_CLUSTER: "#3b82f6",           # blue
    PatternCategory.INTEREST_THEME: "#a855f7",          # purple
    PatternCategory.COLLABORATION_OPPORTUNITY: "#22c55e",  # green
    PatternCategory.COMMUNITY_STRENGTH: "#f97316",      # orange
    PatternCategory.CROSS_DOMAIN: "#ec4899",            # pink
}


@router.get("/data", response_model=GraphDataResponse)
async def get_graph_data(
    pattern_id: Optional[int] = Query(None, description="Filter by pattern ID"),
    edge_types: Optional[List[str]] = Query(None, description="Filter by edge types"),
    skip_cache: bool = Query(False, description="Skip cache and fetch fresh data"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get graph data for visualization.

    Returns nodes (members), edges (connections), and patterns (groupings).
    Results are cached for 5 minutes to improve performance.
    """
    # Check cache first (unless skip_cache is set)
    cache_key = _get_cache_key(pattern_id, edge_types)
    if not skip_cache:
        cached = _get_cached(cache_key)
        if cached:
            return GraphDataResponse(**cached)

    # Fetch all active members (excluding cancelled/expired)
    members_query = select(Member).where(
        Member.membership_status.notin_(['cancelled', 'expired'])
    )

    # If filtering by pattern, only get members in that pattern
    if pattern_id:
        pattern_result = await db.execute(
            select(Pattern).where(Pattern.id == pattern_id)
        )
        pattern = pattern_result.scalar_one_or_none()
        if pattern and pattern.related_member_ids:
            members_query = members_query.where(
                Member.id.in_(pattern.related_member_ids)
            )

    result = await db.execute(members_query.order_by(Member.id))
    members = result.scalars().all()
    member_ids = [m.id for m in members]

    # Fetch edges
    edges_query = select(MemberEdge).where(
        MemberEdge.is_active == True,
        MemberEdge.member_a_id.in_(member_ids),
        MemberEdge.member_b_id.in_(member_ids)
    )

    if edge_types:
        # Convert string types to EdgeType enum values
        type_filters = []
        for et in edge_types:
            try:
                type_filters.append(EdgeType(et))
            except ValueError:
                pass
        if type_filters:
            edges_query = edges_query.where(MemberEdge.edge_type.in_(type_filters))

    edges_result = await db.execute(edges_query)
    edges = edges_result.scalars().all()

    # Count connections per member
    connection_counts = {}
    for edge in edges:
        connection_counts[edge.member_a_id] = connection_counts.get(edge.member_a_id, 0) + 1
        connection_counts[edge.member_b_id] = connection_counts.get(edge.member_b_id, 0) + 1

    # Fetch patterns
    patterns_query = select(Pattern).where(Pattern.is_active == True)
    patterns_result = await db.execute(patterns_query.order_by(Pattern.member_count.desc()))
    patterns = patterns_result.scalars().all()

    # Build member -> pattern mapping
    member_patterns = {m.id: [] for m in members}
    for pattern in patterns:
        if pattern.related_member_ids:
            for mid in pattern.related_member_ids:
                if mid in member_patterns:
                    member_patterns[mid].append(pattern.id)

    # Build response
    nodes = [
        GraphNode(
            id=m.id,
            name=f"{m.first_name or ''} {m.last_name or ''}".strip() or m.email,
            photo_url=m.profile_photo_url,
            pattern_ids=member_patterns.get(m.id, []),
            connection_count=connection_counts.get(m.id, 0),
            skills=m.skills or [],
            interests=m.interests or [],
            role=m.role,
            company=m.company,
            bio=m.bio,
            membership_status=m.membership_status,
        )
        for m in members
    ]

    graph_edges = [
        GraphEdge(
            id=e.id,
            source=e.member_a_id,
            target=e.member_b_id,
            type=e.edge_type.value,
            strength=e.strength,
            evidence=e.evidence,
            discovered_via=e.discovered_via,
        )
        for e in edges
    ]

    graph_patterns = [
        GraphPattern(
            id=p.id,
            name=p.name,
            description=p.description,
            color=PATTERN_COLORS.get(p.category, "#6b7280"),
            member_ids=p.related_member_ids or [],
            category=p.category.value,
        )
        for p in patterns
    ]

    response = GraphDataResponse(
        nodes=nodes,
        edges=graph_edges,
        patterns=graph_patterns,
    )

    # Cache the result
    _set_cache(cache_key, response.model_dump())

    return response


@router.post("/cache/clear")
async def clear_graph_cache():
    """Clear the graph data cache. Use after major data changes."""
    global _graph_cache
    count = len(_graph_cache)
    _graph_cache = {}
    return {"message": f"Cleared {count} cached entries"}


@router.get("/stats")
async def get_graph_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get statistics about the community graph."""
    # Count active members
    members_result = await db.execute(
        select(func.count(Member.id)).where(
            Member.membership_status.notin_(['cancelled', 'expired'])
        )
    )
    member_count = members_result.scalar()

    # Count active edges
    edges_result = await db.execute(
        select(func.count(MemberEdge.id)).where(MemberEdge.is_active == True)
    )
    edge_count = edges_result.scalar()

    # Count patterns
    patterns_result = await db.execute(
        select(func.count(Pattern.id)).where(Pattern.is_active == True)
    )
    pattern_count = patterns_result.scalar()

    # Get edge type distribution
    edge_types_result = await db.execute(
        select(
            MemberEdge.edge_type,
            func.count(MemberEdge.id)
        )
        .where(MemberEdge.is_active == True)
        .group_by(MemberEdge.edge_type)
    )
    edge_type_counts = {
        row[0].value: row[1]
        for row in edge_types_result.all()
    }

    return {
        "member_count": member_count,
        "edge_count": edge_count,
        "pattern_count": pattern_count,
        "edge_type_distribution": edge_type_counts,
    }
