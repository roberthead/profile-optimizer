"""
Event-related API endpoints for the Profile Optimizer.

Provides endpoints for:
- Recording member event signals (interactions)
- Retrieving member event signals
- Getting event recommendations based on taste profile
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import EventSignal, SignalType, Member, TasteProfile
from app.services.rova_client import RovaClient, RovaAPIError, RovaNotFoundError
from app.tools.event_tools import (
    get_member_event_signals,
    record_event_signal,
    get_upcoming_events,
    compute_taste_affinity_scores,
    SIGNAL_STRENGTHS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


# =============================================================================
# Request/Response Models
# =============================================================================


class EventSignalRequest(BaseModel):
    """Request to record a member's interaction with an event."""

    member_id: int = Field(..., description="ID of the member")
    rova_event_id: str = Field(..., description="Rova event ID (e.g., 'event.xxx')")
    rova_event_slug: str = Field(..., description="Rova event slug")
    signal_type: str = Field(
        ...,
        description="Type of interaction",
        json_schema_extra={"enum": ["viewed", "clicked", "rsvp", "attended", "skipped", "shared", "organized"]},
    )
    # Optional denormalized event data for analysis
    event_category: Optional[str] = Field(None, description="Event category name")
    event_venue_slug: Optional[str] = Field(None, description="Venue slug")
    event_organizer_slug: Optional[str] = Field(None, description="Organizer slug")
    event_tags: Optional[List[str]] = Field(default=[], description="Event tags")
    event_time_of_day: Optional[str] = Field(
        None,
        description="Time of day",
        json_schema_extra={"enum": ["morning", "afternoon", "evening", "night"]},
    )
    event_day_of_week: Optional[str] = Field(None, description="Day of week")


class EventSignalResponse(BaseModel):
    """Response after recording an event signal."""

    id: int
    member_id: int
    rova_event_id: str
    rova_event_slug: str
    signal_type: str
    signal_strength: int
    created_at: str


class EventSignalListResponse(BaseModel):
    """Response containing a list of event signals."""

    signals: List[dict]
    count: int
    member_id: int


class EventRecommendation(BaseModel):
    """A recommended event with relevance score."""

    event_id: str
    event_slug: str
    title: str
    venue: Optional[str]
    category: Optional[str]
    starts_at: Optional[str]
    tags: List[str] = []
    relevance_score: float = Field(..., description="0-100 relevance score")
    reasons: List[str] = Field(default=[], description="Why this event is recommended")
    rova_url: Optional[str] = None


class EventRecommendationsResponse(BaseModel):
    """Response containing event recommendations for a member."""

    recommendations: List[EventRecommendation]
    count: int
    member_id: int
    affinity_scores: Optional[dict] = None


class RovaEventListResponse(BaseModel):
    """Response containing events from Rova API."""

    events: List[dict]
    instances: List[dict]
    count: int
    total: int
    page: int
    limit: int


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/signal", response_model=EventSignalResponse)
async def create_event_signal(
    request: EventSignalRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Record a member's interaction with an event.

    Supported signal types:
    - viewed: Member viewed the event details (+10)
    - clicked: Member clicked on event link (+30)
    - rsvp: Member RSVPed to the event (+70)
    - attended: Member attended the event (+100)
    - skipped: Member explicitly skipped/dismissed the event (-30)
    - shared: Member shared the event (+50)
    - organized: Member organized the event (+100)

    The signal_strength is automatically calculated based on signal_type.
    """
    try:
        # Validate signal type
        try:
            signal_type = SignalType(request.signal_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid signal_type: {request.signal_type}. Must be one of: {[t.value for t in SignalType]}",
            )

        result = await record_event_signal(
            db=db,
            member_id=request.member_id,
            rova_event_id=request.rova_event_id,
            rova_event_slug=request.rova_event_slug,
            signal_type=signal_type,
            event_category=request.event_category,
            event_venue_slug=request.event_venue_slug,
            event_organizer_slug=request.event_organizer_slug,
            event_tags=request.event_tags,
            event_time_of_day=request.event_time_of_day,
            event_day_of_week=request.event_day_of_week,
        )

        return EventSignalResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error recording event signal: {e}")
        raise HTTPException(status_code=500, detail="Failed to record event signal")


@router.get("/signals/{member_id}", response_model=EventSignalListResponse)
async def get_member_signals(
    member_id: int,
    signal_type: Optional[str] = Query(None, description="Filter by signal type"),
    limit: int = Query(100, ge=1, le=500, description="Max signals to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a member's event interaction history.

    Returns signals sorted by most recent first, including denormalized
    event data for analysis.
    """
    try:
        # Parse signal types if provided
        signal_types = None
        if signal_type:
            try:
                signal_types = [SignalType(signal_type)]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid signal_type: {signal_type}",
                )

        signals = await get_member_event_signals(
            db=db,
            member_id=member_id,
            signal_types=signal_types,
            limit=limit,
        )

        return EventSignalListResponse(
            signals=signals,
            count=len(signals),
            member_id=member_id,
        )

    except Exception as e:
        logger.exception(f"Error fetching member signals: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch event signals")


@router.get("/recommendations/{member_id}", response_model=EventRecommendationsResponse)
async def get_event_recommendations(
    member_id: int,
    limit: int = Query(10, ge=1, le=50, description="Max recommendations to return"),
    include_affinity_scores: bool = Query(False, description="Include affinity score breakdown"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get personalized event recommendations for a member.

    Recommendations are based on:
    - Member's event signal history (categories, venues, organizers, tags)
    - Taste profile preferences (if available)
    - Upcoming events from Rova

    The relevance_score (0-100) indicates how well the event matches
    the member's inferred preferences.
    """
    try:
        # Verify member exists
        member_result = await db.execute(
            select(Member).where(Member.id == member_id)
        )
        member = member_result.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=404, detail=f"Member {member_id} not found")

        # Compute affinity scores from signals
        affinity_scores = await compute_taste_affinity_scores(db, member_id)

        # Get taste profile if available
        taste_result = await db.execute(
            select(TasteProfile).where(TasteProfile.member_id == member_id)
        )
        taste_profile = taste_result.scalar_one_or_none()

        # Fetch upcoming events from Rova
        try:
            events_response = await get_upcoming_events(limit=limit * 3)  # Fetch more to filter
        except RovaAPIError as e:
            logger.error(f"Error fetching events from Rova: {e.message}")
            raise HTTPException(status_code=502, detail="Failed to fetch events from Rova")

        events = events_response.get("events", [])
        instances = events_response.get("instances", [])

        # Score and rank events
        recommendations: List[EventRecommendation] = []

        for event in events:
            score, reasons = _score_event_for_member(
                event=event,
                affinity_scores=affinity_scores,
                taste_profile=taste_profile,
            )

            # Get primary info
            primary_info = event.get("primaryInfo", {})
            venue = primary_info.get("venue", {})
            categories = primary_info.get("categories", [])
            occurrences = event.get("occurrences", [])

            # Get the next occurrence time
            starts_at = None
            if occurrences:
                starts_at = occurrences[0].get("startsAt")

            # Build the Rova URL
            slug = event.get("slug", "")
            rova_url = f"https://rova.live/events/{slug}" if slug else None

            recommendations.append(
                EventRecommendation(
                    event_id=event.get("id", ""),
                    event_slug=slug,
                    title=primary_info.get("title", ""),
                    venue=venue.get("title") if venue else None,
                    category=categories[0].get("title") if categories else None,
                    starts_at=starts_at,
                    tags=primary_info.get("tags", []),
                    relevance_score=score,
                    reasons=reasons,
                    rova_url=rova_url,
                )
            )

        # Sort by relevance score (descending) and take top N
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        recommendations = recommendations[:limit]

        response_data = {
            "recommendations": recommendations,
            "count": len(recommendations),
            "member_id": member_id,
        }

        if include_affinity_scores:
            response_data["affinity_scores"] = affinity_scores

        return EventRecommendationsResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")


@router.get("/upcoming", response_model=RovaEventListResponse)
async def list_upcoming_events(
    search: Optional[str] = Query(None, description="Full-text search"),
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    venue_slug: Optional[str] = Query(None, description="Filter by venue slug"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    featured: Optional[bool] = Query(None, description="Filter featured events only"),
    page: int = Query(0, ge=0, description="Page number (0-indexed)"),
    limit: int = Query(20, ge=1, le=50, description="Results per page"),
):
    """
    Fetch upcoming events from Rova.

    This is a pass-through to the Rova API with basic filtering support.
    """
    try:
        client = RovaClient()

        # Default to now for upcoming events
        starts_after = datetime.now(timezone.utc).isoformat()

        response = await client.fetch_events(
            page=page,
            limit=limit,
            starts_after=starts_after,
            search=search,
            category_id=category_id,
            venue_slug=venue_slug,
            tags=tags,
            featured=featured,
        )

        return RovaEventListResponse(
            events=response.get("events", []),
            instances=response.get("instances", []),
            count=response.get("count", 0),
            total=response.get("total", 0),
            page=response.get("page", 0),
            limit=response.get("limit", limit),
        )

    except RovaAPIError as e:
        logger.error(f"Error fetching events from Rova: {e.message}")
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Rova API error: {e.message}",
        )


@router.get("/event/{slug}")
async def get_event_details(
    slug: str,
    instance_id: Optional[str] = Query(None, description="Specific occurrence to select"),
):
    """
    Get full details for a specific event by slug.
    """
    try:
        client = RovaClient()
        response = await client.fetch_event_by_slug(slug, instance_id=instance_id)
        return response

    except RovaNotFoundError:
        raise HTTPException(status_code=404, detail=f"Event '{slug}' not found")
    except RovaAPIError as e:
        logger.error(f"Error fetching event from Rova: {e.message}")
        raise HTTPException(status_code=502, detail=f"Rova API error: {e.message}")


# =============================================================================
# Helper Functions
# =============================================================================


def _score_event_for_member(
    event: dict,
    affinity_scores: dict[str, dict[str, float]],
    taste_profile: Optional[TasteProfile],
) -> tuple[float, List[str]]:
    """
    Calculate a relevance score for an event based on member preferences.

    Args:
        event: Rova event object
        affinity_scores: Computed affinity scores from signals
        taste_profile: Member's taste profile (if available)

    Returns:
        Tuple of (score 0-100, list of reasons)
    """
    score = 50.0  # Base score
    reasons: List[str] = []

    primary_info = event.get("primaryInfo", {})

    # Category matching
    categories = primary_info.get("categories", [])
    category_affinities = affinity_scores.get("categories", {})
    for cat in categories:
        cat_title = cat.get("title", "")
        if cat_title in category_affinities:
            affinity = category_affinities[cat_title]
            if affinity > 0:
                score += affinity * 0.3  # Weight category matches
                reasons.append(f"You've enjoyed {cat_title} events")

    # Venue matching
    venue = primary_info.get("venue", {})
    venue_slug = venue.get("slug")
    venue_affinities = affinity_scores.get("venues", {})
    if venue_slug and venue_slug in venue_affinities:
        affinity = venue_affinities[venue_slug]
        if affinity > 0:
            score += affinity * 0.2
            reasons.append(f"You've been to {venue.get('title', 'this venue')} before")

    # Organizer matching
    organizer = primary_info.get("organizer", {})
    org_slug = organizer.get("slug")
    org_affinities = affinity_scores.get("organizers", {})
    if org_slug and org_slug in org_affinities:
        affinity = org_affinities[org_slug]
        if affinity > 0:
            score += affinity * 0.2
            reasons.append(f"Events by {organizer.get('title', 'this organizer')}")

    # Tag matching
    event_tags = primary_info.get("tags", [])
    tag_affinities = affinity_scores.get("tags", {})
    matching_tags = []
    for tag in event_tags:
        if tag in tag_affinities and tag_affinities[tag] > 0:
            score += tag_affinities[tag] * 0.1
            matching_tags.append(tag)
    if matching_tags:
        reasons.append(f"Matches your interests: {', '.join(matching_tags[:3])}")

    # Taste profile matching (if available)
    if taste_profile:
        # Vibe words matching
        if taste_profile.vibe_words:
            event_text = f"{primary_info.get('title', '')} {primary_info.get('description', '')}".lower()
            for vibe in taste_profile.vibe_words:
                if vibe.lower() in event_text:
                    score += 5
                    reasons.append(f"Matches your vibe: {vibe}")

        # Dealbreakers (negative matching)
        if taste_profile.dealbreakers:
            for dealbreaker in taste_profile.dealbreakers:
                if dealbreaker.lower() in event_tags:
                    score -= 30
                    reasons.append(f"Contains dealbreaker: {dealbreaker}")

        # Category affinities from taste profile
        if taste_profile.category_affinities:
            for cat in categories:
                cat_title = cat.get("title", "")
                if cat_title in taste_profile.category_affinities:
                    profile_affinity = taste_profile.category_affinities[cat_title]
                    score += profile_affinity * 0.2

    # Featured events get a small boost
    if event.get("featured"):
        score += 5
        reasons.append("Featured event")

    # Ensure score is within bounds
    score = max(0, min(100, score))

    # Remove duplicate reasons
    reasons = list(dict.fromkeys(reasons))[:5]

    return round(score, 1), reasons
