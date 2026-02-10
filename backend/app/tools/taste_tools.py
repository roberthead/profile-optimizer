"""Tools for taste profile analysis and updates."""

from typing import Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    Member,
    ConversationHistory,
    QuestionResponse,
    EventSignal,
    TasteProfile,
    SignalType,
)


async def get_conversation_history(
    db: AsyncSession,
    member_id: int,
    limit: int = 50,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Retrieve conversation history for a member.

    Args:
        db: Database session.
        member_id: The member's ID.
        limit: Maximum number of messages to retrieve.
        session_id: Optional session ID to filter by.

    Returns:
        Dict with conversation messages and metadata.
    """
    query = (
        select(ConversationHistory)
        .where(ConversationHistory.member_id == member_id)
        .order_by(ConversationHistory.created_at.desc())
        .limit(limit)
    )

    if session_id:
        query = query.where(ConversationHistory.session_id == session_id)

    result = await db.execute(query)
    messages = result.scalars().all()

    # Reverse to get chronological order
    messages = list(reversed(messages))

    return {
        "member_id": member_id,
        "message_count": len(messages),
        "messages": [
            {
                "role": msg.role,
                "content": msg.message_content,
                "session_id": msg.session_id,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ],
    }


async def get_question_responses(
    db: AsyncSession,
    member_id: int,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Retrieve a member's question responses.

    Args:
        db: Database session.
        member_id: The member's ID.
        limit: Maximum number of responses to retrieve.

    Returns:
        Dict with question responses and metadata.
    """
    result = await db.execute(
        select(QuestionResponse)
        .where(QuestionResponse.member_id == member_id)
        .order_by(QuestionResponse.created_at.desc())
        .limit(limit)
    )
    responses = result.scalars().all()

    return {
        "member_id": member_id,
        "response_count": len(responses),
        "responses": [
            {
                "question_id": resp.question_id,
                "response_text": resp.response_text,
                "engagement_rating": resp.engagement_rating,
                "created_at": resp.created_at.isoformat() if resp.created_at else None,
            }
            for resp in responses
        ],
    }


async def get_event_signals(
    db: AsyncSession,
    member_id: int,
    days_back: int = 90,
) -> dict[str, Any]:
    """
    Retrieve a member's event interaction signals.

    Args:
        db: Database session.
        member_id: The member's ID.
        days_back: Number of days to look back.

    Returns:
        Dict with event signals grouped by type.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    result = await db.execute(
        select(EventSignal)
        .where(EventSignal.member_id == member_id)
        .where(EventSignal.created_at >= cutoff)
        .order_by(EventSignal.created_at.desc())
    )
    signals = result.scalars().all()

    # Group by signal type
    by_type: dict[str, list] = {}
    for signal in signals:
        signal_type = signal.signal_type.value
        if signal_type not in by_type:
            by_type[signal_type] = []
        by_type[signal_type].append({
            "rova_event_id": signal.rova_event_id,
            "rova_event_slug": signal.rova_event_slug,
            "signal_strength": signal.signal_strength,
            "event_category": signal.event_category,
            "event_venue_slug": signal.event_venue_slug,
            "event_organizer_slug": signal.event_organizer_slug,
            "event_tags": signal.event_tags or [],
            "event_time_of_day": signal.event_time_of_day,
            "event_day_of_week": signal.event_day_of_week,
            "created_at": signal.created_at.isoformat() if signal.created_at else None,
        })

    # Calculate category/venue/organizer frequencies
    category_counts: dict[str, int] = {}
    venue_counts: dict[str, int] = {}
    organizer_counts: dict[str, int] = {}
    time_of_day_counts: dict[str, int] = {}

    for signal in signals:
        if signal.event_category:
            category_counts[signal.event_category] = category_counts.get(signal.event_category, 0) + signal.signal_strength
        if signal.event_venue_slug:
            venue_counts[signal.event_venue_slug] = venue_counts.get(signal.event_venue_slug, 0) + signal.signal_strength
        if signal.event_organizer_slug:
            organizer_counts[signal.event_organizer_slug] = organizer_counts.get(signal.event_organizer_slug, 0) + signal.signal_strength
        if signal.event_time_of_day:
            time_of_day_counts[signal.event_time_of_day] = time_of_day_counts.get(signal.event_time_of_day, 0) + signal.signal_strength

    return {
        "member_id": member_id,
        "days_analyzed": days_back,
        "total_signals": len(signals),
        "signals_by_type": by_type,
        "aggregated": {
            "category_affinities": dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True)),
            "venue_affinities": dict(sorted(venue_counts.items(), key=lambda x: x[1], reverse=True)),
            "organizer_affinities": dict(sorted(organizer_counts.items(), key=lambda x: x[1], reverse=True)),
            "time_of_day_preference": dict(sorted(time_of_day_counts.items(), key=lambda x: x[1], reverse=True)),
        },
    }


async def get_current_taste_profile(
    db: AsyncSession,
    member_id: int,
) -> dict[str, Any]:
    """
    Retrieve the current taste profile for a member.

    Args:
        db: Database session.
        member_id: The member's ID.

    Returns:
        Dict with current taste profile or empty defaults.
    """
    result = await db.execute(
        select(TasteProfile).where(TasteProfile.member_id == member_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        return {
            "member_id": member_id,
            "exists": False,
            "profile": {
                "vibe_words": [],
                "avoid_words": [],
                "energy_time": None,
                "usual_company": None,
                "spontaneity": 50,
                "dealbreakers": [],
                "not_my_thing": [],
                "category_affinities": {},
                "venue_affinities": {},
                "organizer_affinities": {},
                "price_comfort": None,
                "current_mood": None,
                "this_week_energy": None,
                "visitors_in_town": False,
            },
        }

    return {
        "member_id": member_id,
        "exists": True,
        "profile_id": profile.id,
        "profile": {
            "vibe_words": profile.vibe_words or [],
            "avoid_words": profile.avoid_words or [],
            "energy_time": profile.energy_time,
            "usual_company": profile.usual_company,
            "spontaneity": profile.spontaneity,
            "dealbreakers": profile.dealbreakers or [],
            "not_my_thing": profile.not_my_thing or [],
            "category_affinities": profile.category_affinities or {},
            "venue_affinities": profile.venue_affinities or {},
            "organizer_affinities": profile.organizer_affinities or {},
            "price_comfort": profile.price_comfort,
            "current_mood": profile.current_mood,
            "this_week_energy": profile.this_week_energy,
            "visitors_in_town": profile.visitors_in_town,
            "context_updated_at": profile.context_updated_at.isoformat() if profile.context_updated_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        },
    }


async def update_taste_profile(
    db: AsyncSession,
    member_id: int,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """
    Update or create a taste profile for a member.

    Args:
        db: Database session.
        member_id: The member's ID.
        updates: Dict of fields to update.

    Returns:
        Dict with success status and updated profile.
    """
    # Verify member exists
    member_result = await db.execute(
        select(Member).where(Member.id == member_id)
    )
    member = member_result.scalar_one_or_none()
    if not member:
        return {"error": f"Member {member_id} not found", "success": False}

    # Get or create taste profile
    result = await db.execute(
        select(TasteProfile).where(TasteProfile.member_id == member_id)
    )
    profile = result.scalar_one_or_none()

    was_created = profile is None

    if not profile:
        profile = TasteProfile(member_id=member_id)
        db.add(profile)

    # Update explicit preferences
    if "vibe_words" in updates:
        profile.vibe_words = updates["vibe_words"]
    if "avoid_words" in updates:
        profile.avoid_words = updates["avoid_words"]
    if "energy_time" in updates:
        profile.energy_time = updates["energy_time"]
    if "usual_company" in updates:
        profile.usual_company = updates["usual_company"]
    if "spontaneity" in updates:
        profile.spontaneity = updates["spontaneity"]
    if "dealbreakers" in updates:
        profile.dealbreakers = updates["dealbreakers"]
    if "not_my_thing" in updates:
        profile.not_my_thing = updates["not_my_thing"]

    # Update implicit preferences (from behavior)
    if "category_affinities" in updates:
        profile.category_affinities = updates["category_affinities"]
    if "venue_affinities" in updates:
        profile.venue_affinities = updates["venue_affinities"]
    if "organizer_affinities" in updates:
        profile.organizer_affinities = updates["organizer_affinities"]
    if "price_comfort" in updates:
        profile.price_comfort = updates["price_comfort"]

    # Update contextual state
    if "current_mood" in updates:
        profile.current_mood = updates["current_mood"]
    if "this_week_energy" in updates:
        profile.this_week_energy = updates["this_week_energy"]
    if "visitors_in_town" in updates:
        profile.visitors_in_town = updates["visitors_in_town"]

    # If any contextual fields were updated, set the context timestamp
    context_fields = {"current_mood", "this_week_energy", "visitors_in_town"}
    if context_fields.intersection(updates.keys()):
        profile.context_updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(profile)

    return {
        "success": True,
        "member_id": member_id,
        "profile_id": profile.id,
        "created": was_created,
        "updated_fields": list(updates.keys()),
    }


# Tool definitions for Claude API

GET_CONVERSATION_HISTORY_TOOL = {
    "name": "get_conversation_history",
    "description": """Retrieve past conversation messages with a member.

Returns chronologically ordered messages including:
- role (user/assistant)
- content
- session_id
- created_at

Use this to analyze conversational patterns, detect vibe words, avoid words,
and preference signals from how the member naturally expresses themselves.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The member's database ID"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum messages to retrieve (default: 50)",
                "default": 50
            },
            "session_id": {
                "type": "string",
                "description": "Optional: filter to a specific conversation session"
            }
        },
        "required": ["member_id"]
    }
}


GET_QUESTION_RESPONSES_TOOL = {
    "name": "get_question_responses",
    "description": """Retrieve a member's answers to community questions.

Returns their responses including:
- question_id
- response_text
- engagement_rating
- created_at

Analyze these for preference signals, interests, and personality traits.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The member's database ID"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum responses to retrieve (default: 100)",
                "default": 100
            }
        },
        "required": ["member_id"]
    }
}


GET_EVENT_SIGNALS_TOOL = {
    "name": "get_event_signals",
    "description": """Retrieve a member's Rova event interaction signals.

Returns behavioral data including:
- Signal types: viewed, clicked, rsvp, attended, skipped, shared, organized
- Event metadata: category, venue, organizer, tags, time of day, day of week
- Aggregated affinities calculated from signal strengths

This is implicit preference data - what they actually do vs what they say.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The member's database ID"
            },
            "days_back": {
                "type": "integer",
                "description": "Number of days to analyze (default: 90)",
                "default": 90
            }
        },
        "required": ["member_id"]
    }
}


GET_CURRENT_TASTE_PROFILE_TOOL = {
    "name": "get_current_taste_profile",
    "description": """Retrieve the current taste profile for a member.

Returns all preference data including:
- Explicit: vibe_words, avoid_words, energy_time, usual_company, spontaneity
- Anti-preferences: dealbreakers, not_my_thing
- Implicit (from behavior): category/venue/organizer affinities, price_comfort
- Contextual (temporary): current_mood, this_week_energy, visitors_in_town

Returns empty defaults if no profile exists yet.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The member's database ID"
            }
        },
        "required": ["member_id"]
    }
}


UPDATE_TASTE_PROFILE_TOOL = {
    "name": "update_taste_profile",
    "description": """Update or create a taste profile for a member.

Accepts partial updates - only include fields you want to change.

Explicit preferences:
- vibe_words: ["cozy", "weird", "intimate"] - words that resonate
- avoid_words: ["crowded", "loud", "mainstream"] - words that repel
- energy_time: "morning" | "afternoon" | "evening" | "night"
- usual_company: "solo" | "duo" | "group" | "varies"
- spontaneity: 0-100 (0=planner, 100=spontaneous)
- dealbreakers: ["standing room", "cash only"] - hard nos
- not_my_thing: ["karaoke", "networking events"] - soft avoids

Implicit preferences (from behavior):
- category_affinities: {"Live Music": 80, "Workshops": -20}
- venue_affinities: {"Varsity Theatre": 90, "downtown": -50}
- organizer_affinities: {"Ashland Folk Collective": 80}
- price_comfort: {"min": 0, "max": 50, "sweet_spot": 15}

Contextual state (temporary):
- current_mood: "adventurous" | "low-key" | etc.
- this_week_energy: "low" | "medium" | "high"
- visitors_in_town: true/false""",
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "integer",
                "description": "The member's database ID"
            },
            "updates": {
                "type": "object",
                "description": "Fields to update (partial update supported)",
                "properties": {
                    "vibe_words": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Words that resonate with them"
                    },
                    "avoid_words": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Words that repel them"
                    },
                    "energy_time": {
                        "type": "string",
                        "enum": ["morning", "afternoon", "evening", "night"],
                        "description": "When they prefer to go out"
                    },
                    "usual_company": {
                        "type": "string",
                        "enum": ["solo", "duo", "group", "varies"],
                        "description": "Who they usually attend with"
                    },
                    "spontaneity": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "0=planner, 100=spontaneous"
                    },
                    "dealbreakers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Hard no's that prevent attendance"
                    },
                    "not_my_thing": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Things they just don't get"
                    },
                    "category_affinities": {
                        "type": "object",
                        "description": "Category -> affinity score (-100 to 100)"
                    },
                    "venue_affinities": {
                        "type": "object",
                        "description": "Venue/area -> affinity score (-100 to 100)"
                    },
                    "organizer_affinities": {
                        "type": "object",
                        "description": "Organizer -> affinity score (-100 to 100)"
                    },
                    "price_comfort": {
                        "type": "object",
                        "description": "Price range: {min, max, sweet_spot}"
                    },
                    "current_mood": {
                        "type": "string",
                        "description": "Current temporary mood"
                    },
                    "this_week_energy": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Energy level this week"
                    },
                    "visitors_in_town": {
                        "type": "boolean",
                        "description": "Whether they have visitors"
                    }
                }
            }
        },
        "required": ["member_id", "updates"]
    }
}
