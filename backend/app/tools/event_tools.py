"""Tools for event-related operations that can be used by LLM agents."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EventSignal, SignalType, Member, TasteProfile
from app.services.rova_client import RovaClient, RovaAPIError

logger = logging.getLogger(__name__)


# Signal strength values for different interaction types
SIGNAL_STRENGTHS = {
    SignalType.ATTENDED: 100,
    SignalType.ORGANIZED: 100,
    SignalType.RSVP: 70,
    SignalType.SHARED: 50,
    SignalType.CLICKED: 30,
    SignalType.VIEWED: 10,
    SignalType.SKIPPED: -30,
}


async def get_member_event_signals(
    db: AsyncSession,
    member_id: int,
    signal_types: Optional[list[SignalType]] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Get event signals for a member for taste profile analysis.

    Args:
        db: Database session
        member_id: The member to get signals for
        signal_types: Optional filter by signal types
        limit: Maximum number of signals to return

    Returns:
        List of event signal dictionaries with denormalized event data
    """
    logger.info(f"Fetching event signals for member {member_id}")

    query = (
        select(EventSignal)
        .where(EventSignal.member_id == member_id)
        .order_by(EventSignal.created_at.desc())
        .limit(limit)
    )

    if signal_types:
        query = query.where(EventSignal.signal_type.in_(signal_types))

    result = await db.execute(query)
    signals = result.scalars().all()

    return [
        {
            "id": signal.id,
            "rova_event_id": signal.rova_event_id,
            "rova_event_slug": signal.rova_event_slug,
            "signal_type": signal.signal_type.value,
            "signal_strength": signal.signal_strength,
            "event_category": signal.event_category,
            "event_venue_slug": signal.event_venue_slug,
            "event_organizer_slug": signal.event_organizer_slug,
            "event_tags": signal.event_tags or [],
            "event_time_of_day": signal.event_time_of_day,
            "event_day_of_week": signal.event_day_of_week,
            "created_at": signal.created_at.isoformat() if signal.created_at else None,
        }
        for signal in signals
    ]


async def record_event_signal(
    db: AsyncSession,
    member_id: int,
    rova_event_id: str,
    rova_event_slug: str,
    signal_type: SignalType,
    event_category: Optional[str] = None,
    event_venue_slug: Optional[str] = None,
    event_organizer_slug: Optional[str] = None,
    event_tags: Optional[list[str]] = None,
    event_time_of_day: Optional[str] = None,
    event_day_of_week: Optional[str] = None,
) -> dict[str, Any]:
    """
    Record a member's interaction with an event.

    Args:
        db: Database session
        member_id: The member who interacted
        rova_event_id: Rova event ID (e.g., "event.xxx")
        rova_event_slug: Rova event slug
        signal_type: Type of interaction
        event_category: Event category for denormalized lookup
        event_venue_slug: Venue slug for denormalized lookup
        event_organizer_slug: Organizer slug for denormalized lookup
        event_tags: Event tags for denormalized lookup
        event_time_of_day: Time of day (morning, afternoon, evening, night)
        event_day_of_week: Day of week

    Returns:
        Created signal data
    """
    logger.info(
        f"Recording event signal: member={member_id}, event={rova_event_slug}, type={signal_type.value}"
    )

    # Verify member exists
    member_result = await db.execute(
        select(Member).where(Member.id == member_id)
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise ValueError(f"Member {member_id} not found")

    # Get signal strength
    signal_strength = SIGNAL_STRENGTHS.get(signal_type, 0)

    # Create the signal
    signal = EventSignal(
        member_id=member_id,
        rova_event_id=rova_event_id,
        rova_event_slug=rova_event_slug,
        signal_type=signal_type,
        signal_strength=signal_strength,
        event_category=event_category,
        event_venue_slug=event_venue_slug,
        event_organizer_slug=event_organizer_slug,
        event_tags=event_tags or [],
        event_time_of_day=event_time_of_day,
        event_day_of_week=event_day_of_week,
    )

    db.add(signal)
    await db.commit()
    await db.refresh(signal)

    logger.info(f"Recorded event signal {signal.id}")

    return {
        "id": signal.id,
        "member_id": signal.member_id,
        "rova_event_id": signal.rova_event_id,
        "rova_event_slug": signal.rova_event_slug,
        "signal_type": signal.signal_type.value,
        "signal_strength": signal.signal_strength,
        "created_at": signal.created_at.isoformat() if signal.created_at else None,
    }


async def get_upcoming_events(
    starts_after: Optional[str] = None,
    starts_before: Optional[str] = None,
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    venue_slug: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Fetch upcoming events from Rova API.

    Args:
        starts_after: ISO timestamp for start window (defaults to now)
        starts_before: ISO timestamp for end window
        search: Full-text search term
        category_id: Filter by category ID
        venue_slug: Filter by venue slug
        tags: Comma-separated tag filter
        limit: Max events to return

    Returns:
        Dict with events and instances from Rova API
    """
    logger.info("Fetching upcoming events from Rova")

    try:
        client = RovaClient()

        # Default to now if no start time specified
        if not starts_after:
            starts_after = datetime.now(timezone.utc).isoformat()

        response = await client.fetch_events(
            starts_after=starts_after,
            starts_before=starts_before,
            search=search,
            category_id=category_id,
            venue_slug=venue_slug,
            tags=tags,
            limit=limit,
        )

        return response

    except RovaAPIError as e:
        logger.error(f"Error fetching events from Rova: {e.message}")
        raise


async def compute_taste_affinity_scores(
    db: AsyncSession,
    member_id: int,
) -> dict[str, dict[str, float]]:
    """
    Compute affinity scores from a member's event signals.

    Analyzes event signals to calculate affinity scores for:
    - Categories
    - Venues
    - Organizers
    - Tags
    - Time of day
    - Day of week

    Args:
        db: Database session
        member_id: Member to compute scores for

    Returns:
        Dict with affinity scores by dimension
    """
    logger.info(f"Computing taste affinity scores for member {member_id}")

    # Get all signals for the member
    signals = await get_member_event_signals(db, member_id, limit=500)

    if not signals:
        return {
            "categories": {},
            "venues": {},
            "organizers": {},
            "tags": {},
            "time_of_day": {},
            "day_of_week": {},
        }

    # Initialize accumulators
    category_scores: dict[str, float] = {}
    venue_scores: dict[str, float] = {}
    organizer_scores: dict[str, float] = {}
    tag_scores: dict[str, float] = {}
    time_scores: dict[str, float] = {}
    day_scores: dict[str, float] = {}

    # Process each signal
    for signal in signals:
        strength = signal["signal_strength"]

        # Category affinity
        if signal["event_category"]:
            cat = signal["event_category"]
            category_scores[cat] = category_scores.get(cat, 0) + strength

        # Venue affinity
        if signal["event_venue_slug"]:
            venue = signal["event_venue_slug"]
            venue_scores[venue] = venue_scores.get(venue, 0) + strength

        # Organizer affinity
        if signal["event_organizer_slug"]:
            org = signal["event_organizer_slug"]
            organizer_scores[org] = organizer_scores.get(org, 0) + strength

        # Tag affinities
        for tag in signal["event_tags"]:
            tag_scores[tag] = tag_scores.get(tag, 0) + strength

        # Time of day affinity
        if signal["event_time_of_day"]:
            time = signal["event_time_of_day"]
            time_scores[time] = time_scores.get(time, 0) + strength

        # Day of week affinity
        if signal["event_day_of_week"]:
            day = signal["event_day_of_week"]
            day_scores[day] = day_scores.get(day, 0) + strength

    # Normalize scores to 0-100 range
    def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
        if not scores:
            return {}
        max_score = max(abs(v) for v in scores.values()) if scores else 1
        if max_score == 0:
            return scores
        return {k: min(100, max(-100, int((v / max_score) * 100))) for k, v in scores.items()}

    return {
        "categories": normalize_scores(category_scores),
        "venues": normalize_scores(venue_scores),
        "organizers": normalize_scores(organizer_scores),
        "tags": normalize_scores(tag_scores),
        "time_of_day": normalize_scores(time_scores),
        "day_of_week": normalize_scores(day_scores),
    }


# Tool definitions for Claude API
GET_EVENT_SIGNALS_TOOL = {
    "name": "get_member_event_signals",
    "description": "Get a member's event interaction history (views, clicks, RSVPs, attendances, skips). Use this to understand what kinds of events a member is interested in for taste profile analysis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The ID of the member whose event signals to retrieve"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of signals to return (default 100)"
            }
        },
        "required": ["member_id"]
    }
}


RECORD_EVENT_SIGNAL_TOOL = {
    "name": "record_event_signal",
    "description": "Record a member's interaction with an event (view, click, RSVP, attendance, skip). Use this when a member expresses interest in or interacts with a Rova event.",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The ID of the member who interacted with the event"
            },
            "rova_event_id": {
                "type": "string",
                "description": "The Rova event ID (e.g., 'event.xxx')"
            },
            "rova_event_slug": {
                "type": "string",
                "description": "The Rova event slug"
            },
            "signal_type": {
                "type": "string",
                "description": "Type of interaction",
                "enum": ["viewed", "clicked", "rsvp", "attended", "skipped", "shared", "organized"]
            },
            "event_category": {
                "type": "string",
                "description": "Event category name"
            },
            "event_venue_slug": {
                "type": "string",
                "description": "Venue slug"
            },
            "event_tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Event tags"
            }
        },
        "required": ["member_id", "rova_event_id", "rova_event_slug", "signal_type"]
    }
}


GET_UPCOMING_EVENTS_TOOL = {
    "name": "get_upcoming_events",
    "description": "Fetch upcoming events from Rova. Use this to find events to recommend to members or to search for specific types of events.",
    "input_schema": {
        "type": "object",
        "properties": {
            "search": {
                "type": "string",
                "description": "Full-text search across event titles, venues, categories, artists, tags"
            },
            "category_id": {
                "type": "string",
                "description": "Filter by category ID (e.g., 'category.music')"
            },
            "venue_slug": {
                "type": "string",
                "description": "Filter by venue slug"
            },
            "tags": {
                "type": "string",
                "description": "Comma-separated tags to filter by"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of events to return (default 20, max 50)"
            }
        },
        "required": []
    }
}
