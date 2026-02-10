"""
Message templates and previews for email and SMS communications.

These endpoints generate personalized message content for member engagement:
- Weekly digest emails with connections, questions, and event recommendations
- Event recommendation emails with taste profile matching
- SMS question nudges from targeted question queues
- SMS event alerts with connection context
- SMS connection nudges for introductions
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta, timezone
import random

from app.core.database import get_db
from app.models import (
    Member, ProfileCompleteness, Pattern, MemberEdge, TasteProfile,
    Question, QuestionDeck, EdgeType, PatternCategory
)


router = APIRouter(prefix="/messages", tags=["messages"])


# =============================================================================
# Response Models
# =============================================================================

class EmailContent(BaseModel):
    subject: str
    html: str
    plain_text: str


class SMSContent(BaseModel):
    text: str
    character_count: int
    is_within_limit: bool


class ConnectionDiscovery(BaseModel):
    member_id: int
    member_name: str
    connection_reason: str
    shared_items: List[str]


class EventRecommendation(BaseModel):
    event_slug: str
    event_title: str
    match_reasons: List[str]
    friends_going: List[str]


class GraphStats(BaseModel):
    completeness_score: int
    total_connections: int
    patterns_matched: int
    questions_answered: int


# =============================================================================
# Helper Functions
# =============================================================================

async def get_member_or_404(db: AsyncSession, member_id: int) -> Member:
    """Fetch a member by ID or raise 404."""
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


async def get_member_connections(db: AsyncSession, member_id: int, limit: int = 5) -> List[ConnectionDiscovery]:
    """Get recent connections discovered for a member."""
    result = await db.execute(
        select(MemberEdge)
        .where(
            (MemberEdge.member_a_id == member_id) | (MemberEdge.member_b_id == member_id)
        )
        .where(MemberEdge.is_active == True)
        .order_by(MemberEdge.created_at.desc())
        .limit(limit)
    )
    edges = result.scalars().all()

    connections = []
    for edge in edges:
        other_id = edge.member_b_id if edge.member_a_id == member_id else edge.member_a_id
        other_result = await db.execute(select(Member).where(Member.id == other_id))
        other_member = other_result.scalar_one_or_none()

        if other_member:
            name = f"{other_member.first_name or ''} {other_member.last_name or ''}".strip() or "A community member"

            # Build connection reason based on edge type
            reason_map = {
                EdgeType.SHARED_SKILL: "You share similar skills",
                EdgeType.SHARED_INTEREST: "You share common interests",
                EdgeType.COLLABORATION_POTENTIAL: "Great collaboration potential",
                EdgeType.EVENT_CO_ATTENDANCE: "You've attended events together",
                EdgeType.INTRODUCED_BY_AGENT: "We thought you'd click",
                EdgeType.PATTERN_CONNECTION: "You're part of the same community pattern",
            }
            reason = reason_map.get(edge.edge_type, "Connected through the community")

            shared = []
            if edge.evidence:
                shared = edge.evidence.get("shared_skills", [])[:3] or edge.evidence.get("shared_interests", [])[:3]

            connections.append(ConnectionDiscovery(
                member_id=other_id,
                member_name=name,
                connection_reason=reason,
                shared_items=shared
            ))

    return connections


async def get_member_graph_stats(db: AsyncSession, member_id: int) -> GraphStats:
    """Get graph statistics for a member."""
    # Completeness score
    completeness_result = await db.execute(
        select(ProfileCompleteness).where(ProfileCompleteness.member_id == member_id)
    )
    completeness = completeness_result.scalar_one_or_none()
    score = int(completeness.completeness_score) if completeness else 0

    # Total connections
    edge_count_result = await db.execute(
        select(func.count())
        .select_from(MemberEdge)
        .where(
            ((MemberEdge.member_a_id == member_id) | (MemberEdge.member_b_id == member_id))
            & (MemberEdge.is_active == True)
        )
    )
    total_connections = edge_count_result.scalar() or 0

    # Patterns matched (simplified - count patterns where member is in related_member_ids)
    patterns_result = await db.execute(
        select(func.count())
        .select_from(Pattern)
        .where(Pattern.is_active == True)
    )
    patterns_count = patterns_result.scalar() or 0

    return GraphStats(
        completeness_score=score,
        total_connections=total_connections,
        patterns_matched=patterns_count,
        questions_answered=0  # Would need QuestionResponse count
    )


async def get_personalized_question(db: AsyncSession, member_id: int) -> Optional[str]:
    """Get a personalized question for the member from their targeted queue."""
    # Try to get a question from a personalized deck first
    result = await db.execute(
        select(Question)
        .join(QuestionDeck)
        .where(QuestionDeck.member_id == member_id)
        .where(Question.is_active == True)
        .order_by(func.random())
        .limit(1)
    )
    question = result.scalar_one_or_none()

    # Fall back to global deck
    if not question:
        result = await db.execute(
            select(Question)
            .join(QuestionDeck)
            .where(QuestionDeck.member_id.is_(None))
            .where(Question.is_active == True)
            .order_by(func.random())
            .limit(1)
        )
        question = result.scalar_one_or_none()

    return question.question_text if question else None


def generate_email_html(
    member_name: str,
    subject: str,
    intro_text: str,
    sections: List[dict],
    cta_text: Optional[str] = None,
    cta_url: Optional[str] = None
) -> str:
    """Generate HTML email content with White Rabbit branding."""

    sections_html = ""
    for section in sections:
        section_content = ""
        if section.get("type") == "connections":
            for conn in section.get("items", []):
                section_content += f"""
                <div style="padding: 12px; background: #f8f9fa; border-radius: 8px; margin-bottom: 8px;">
                    <strong style="color: #1a1a2e;">{conn['name']}</strong>
                    <p style="margin: 4px 0 0; color: #666; font-size: 14px;">{conn['reason']}</p>
                    {f'<p style="margin: 4px 0 0; color: #888; font-size: 13px;">Shared: {", ".join(conn.get("shared", []))}</p>' if conn.get("shared") else ''}
                </div>
                """
        elif section.get("type") == "question":
            section_content = f"""
            <div style="padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; color: white;">
                <p style="margin: 0; font-size: 16px; font-style: italic;">"{section.get('question', '')}"</p>
                <a href="#" style="display: inline-block; margin-top: 12px; padding: 8px 16px; background: white; color: #667eea; text-decoration: none; border-radius: 4px; font-size: 14px; font-weight: 500;">Answer Now</a>
            </div>
            """
        elif section.get("type") == "events":
            for event in section.get("items", []):
                section_content += f"""
                <div style="padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 8px;">
                    <strong style="color: #1a1a2e;">{event['title']}</strong>
                    <p style="margin: 4px 0 0; color: #666; font-size: 14px;">{', '.join(event.get('reasons', []))}</p>
                    {f'<p style="margin: 4px 0 0; color: #667eea; font-size: 13px;">Friends going: {", ".join(event.get("friends", []))}</p>' if event.get("friends") else ''}
                </div>
                """
        elif section.get("type") == "stats":
            stats = section.get("stats", {})
            section_content = f"""
            <div style="display: flex; flex-wrap: wrap; gap: 16px;">
                <div style="flex: 1; min-width: 120px; padding: 12px; background: #f0f4ff; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #667eea;">{stats.get('completeness', 0)}%</div>
                    <div style="font-size: 12px; color: #666;">Profile Complete</div>
                </div>
                <div style="flex: 1; min-width: 120px; padding: 12px; background: #f0fff4; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #38a169;">{stats.get('connections', 0)}</div>
                    <div style="font-size: 12px; color: #666;">Connections</div>
                </div>
                <div style="flex: 1; min-width: 120px; padding: 12px; background: #fff5f5; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #e53e3e;">{stats.get('patterns', 0)}</div>
                    <div style="font-size: 12px; color: #666;">Patterns</div>
                </div>
            </div>
            """
        else:
            section_content = section.get("content", "")

        sections_html += f"""
        <div style="margin-bottom: 24px;">
            <h2 style="margin: 0 0 12px; font-size: 18px; color: #1a1a2e;">{section.get('title', '')}</h2>
            {section_content}
        </div>
        """

    cta_html = ""
    if cta_text and cta_url:
        cta_html = f"""
        <div style="text-align: center; margin: 32px 0;">
            <a href="{cta_url}" style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">{cta_text}</a>
        </div>
        """

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 20px 0;">
                <table role="presentation" style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 24px 32px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);">
                            <table role="presentation" style="width: 100%;">
                                <tr>
                                    <td>
                                        <span style="font-size: 28px;">&#x1F430;</span>
                                        <span style="color: white; font-size: 20px; font-weight: bold; margin-left: 8px; vertical-align: middle;">White Rabbit</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding: 32px;">
                            <h1 style="margin: 0 0 8px; font-size: 24px; color: #1a1a2e;">Hey {member_name}!</h1>
                            <p style="margin: 0 0 24px; color: #666; font-size: 16px; line-height: 1.5;">{intro_text}</p>

                            {sections_html}

                            {cta_html}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 32px; background: #f8f9fa; border-top: 1px solid #e0e0e0;">
                            <p style="margin: 0 0 8px; color: #666; font-size: 14px;">White Rabbit Ashland - Where creators connect</p>
                            <p style="margin: 0; font-size: 12px; color: #999;">
                                Generated with <a href="https://claude.ai/code" style="color: #667eea; text-decoration: none;">Claude Code</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def generate_plain_text(
    member_name: str,
    intro_text: str,
    sections: List[dict]
) -> str:
    """Generate plain text version of email."""
    lines = [
        f"Hey {member_name}!",
        "",
        intro_text,
        "",
    ]

    for section in sections:
        lines.append(f"## {section.get('title', '')}")
        lines.append("")

        if section.get("type") == "connections":
            for conn in section.get("items", []):
                lines.append(f"- {conn['name']}: {conn['reason']}")
                if conn.get("shared"):
                    lines.append(f"  Shared: {', '.join(conn['shared'])}")
        elif section.get("type") == "question":
            lines.append(f'"{section.get("question", "")}"')
        elif section.get("type") == "events":
            for event in section.get("items", []):
                lines.append(f"- {event['title']}")
                lines.append(f"  Why: {', '.join(event.get('reasons', []))}")
        elif section.get("type") == "stats":
            stats = section.get("stats", {})
            lines.append(f"Profile: {stats.get('completeness', 0)}% complete")
            lines.append(f"Connections: {stats.get('connections', 0)}")
            lines.append(f"Patterns: {stats.get('patterns', 0)}")
        else:
            lines.append(section.get("content", ""))

        lines.append("")

    lines.extend([
        "---",
        "White Rabbit Ashland - Where creators connect",
        "Generated with Claude Code (https://claude.ai/code)",
    ])

    return "\n".join(lines)


# =============================================================================
# Email Endpoints
# =============================================================================

@router.get("/email/weekly-digest/{member_id}", response_model=EmailContent)
async def get_weekly_digest_email(
    member_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate weekly digest email content for a member.

    Includes:
    - New connections discovered for this member
    - A personalized question for them
    - Event recommendations based on taste profile
    - Their graph stats (completeness, connections, patterns)
    """
    member = await get_member_or_404(db, member_id)
    member_name = member.first_name or "there"

    # Gather content
    connections = await get_member_connections(db, member_id, limit=3)
    question = await get_personalized_question(db, member_id)
    stats = await get_member_graph_stats(db, member_id)

    # Build sections
    sections = []

    if connections:
        sections.append({
            "title": f"{len(connections)} New Connections Discovered",
            "type": "connections",
            "items": [
                {
                    "name": c.member_name,
                    "reason": c.connection_reason,
                    "shared": c.shared_items
                }
                for c in connections
            ]
        })

    if question:
        sections.append({
            "title": "Quick Question for You",
            "type": "question",
            "question": question
        })

    # Mock event recommendations (would come from Rova integration)
    sections.append({
        "title": "Events We Think You'll Love",
        "type": "events",
        "items": [
            {
                "title": "Creator Meetup at The Hive",
                "reasons": ["Matches your creative interests", "Intimate venue"],
                "friends": [c.member_name for c in connections[:2]] if connections else []
            }
        ]
    })

    sections.append({
        "title": "Your Community Stats",
        "type": "stats",
        "stats": {
            "completeness": stats.completeness_score,
            "connections": stats.total_connections,
            "patterns": stats.patterns_matched
        }
    })

    subject = f"Your White Rabbit Week: {len(connections)} new connections discovered"
    intro_text = "Here's what's been happening in your corner of the White Rabbit community."

    html = generate_email_html(
        member_name=member_name,
        subject=subject,
        intro_text=intro_text,
        sections=sections,
        cta_text="Explore Your Connections",
        cta_url="https://whiterabbitashland.com/profile"
    )

    plain_text = generate_plain_text(
        member_name=member_name,
        intro_text=intro_text,
        sections=sections
    )

    return EmailContent(
        subject=subject,
        html=html,
        plain_text=plain_text
    )


@router.get("/email/event-recommendation/{member_id}", response_model=EmailContent)
async def get_event_recommendation_email(
    member_id: int,
    event_slug: str = "community-gathering",
    db: AsyncSession = Depends(get_db)
):
    """
    Generate event recommendation email for a specific event.

    Includes:
    - Event details
    - Why we thought of them (taste profile match reasons)
    - Who else they know is going
    """
    member = await get_member_or_404(db, member_id)
    member_name = member.first_name or "there"

    # Get connections for "friends going" section
    connections = await get_member_connections(db, member_id, limit=3)
    friends_going = [c.member_name for c in connections[:2]] if connections else []

    # Get member's taste profile for match reasons
    taste_result = await db.execute(
        select(TasteProfile).where(TasteProfile.member_id == member_id)
    )
    taste_profile = taste_result.scalar_one_or_none()

    # Build match reasons based on taste profile
    match_reasons = []
    if taste_profile:
        if taste_profile.vibe_words:
            match_reasons.append(f"Matches your vibe: {', '.join(taste_profile.vibe_words[:2])}")
        if taste_profile.energy_time:
            match_reasons.append(f"Perfect for your {taste_profile.energy_time} energy")

    if member.interests:
        match_reasons.append(f"Aligns with your interest in {random.choice(member.interests)}")

    if not match_reasons:
        match_reasons = ["We think you'll love the people", "It's your kind of gathering"]

    # Mock event details (would come from Rova API)
    event_title = "Community Creator Showcase"
    event_date = "Saturday, February 15th at 7:00 PM"
    event_venue = "The Hive Collective"
    event_description = "An evening celebrating the creative spirit of our community. Share your work, connect with fellow creators, and discover new collaborations."

    sections = [
        {
            "title": "Event Details",
            "type": "custom",
            "content": f"""
            <div style="padding: 16px; background: #f8f9fa; border-radius: 8px;">
                <h3 style="margin: 0 0 8px; color: #1a1a2e;">{event_title}</h3>
                <p style="margin: 0 0 8px; color: #666;">{event_date}</p>
                <p style="margin: 0 0 12px; color: #666;">{event_venue}</p>
                <p style="margin: 0; color: #444; font-size: 14px;">{event_description}</p>
            </div>
            """
        },
        {
            "title": "Why We Thought of You",
            "type": "custom",
            "content": "<ul style='margin: 0; padding-left: 20px;'>" +
                       "".join([f"<li style='color: #666; margin-bottom: 4px;'>{reason}</li>" for reason in match_reasons]) +
                       "</ul>"
        }
    ]

    if friends_going:
        sections.append({
            "title": "Friends Who Are Going",
            "type": "custom",
            "content": f"<p style='color: #667eea; margin: 0;'>{', '.join(friends_going)}</p>"
        })

    subject = f"{member_name}, this looks like your kind of thing"
    intro_text = "We found an event that seems perfect for you based on your interests and connections."

    html = generate_email_html(
        member_name=member_name,
        subject=subject,
        intro_text=intro_text,
        sections=sections,
        cta_text="View Event Details",
        cta_url=f"https://rfrsh.rova.events/{event_slug}"
    )

    plain_text = generate_plain_text(
        member_name=member_name,
        intro_text=intro_text,
        sections=[
            {
                "title": "Event Details",
                "type": "custom",
                "content": f"{event_title}\n{event_date}\n{event_venue}\n\n{event_description}"
            },
            {
                "title": "Why We Thought of You",
                "type": "custom",
                "content": "\n".join([f"- {reason}" for reason in match_reasons])
            }
        ]
    )

    return EmailContent(
        subject=subject,
        html=html,
        plain_text=plain_text
    )


# =============================================================================
# SMS Endpoints
# =============================================================================

SMS_LIMIT = 160


def create_sms_content(text: str) -> SMSContent:
    """Create SMS content with character count tracking."""
    char_count = len(text)
    return SMSContent(
        text=text,
        character_count=char_count,
        is_within_limit=char_count <= SMS_LIMIT
    )


@router.get("/sms/question-nudge/{member_id}", response_model=SMSContent)
async def get_question_nudge_sms(
    member_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate SMS text with a quick question from their targeted queue.

    Under 160 characters with reply instructions.
    """
    member = await get_member_or_404(db, member_id)

    question = await get_personalized_question(db, member_id)

    # Default questions if none in queue
    fallback_questions = [
        "What's a skill you'd love to borrow from someone here?",
        "What project are you most excited about right now?",
        "What's something unexpected about your creative process?",
        "Who in the community would you like to know better?",
    ]

    question_text = question or random.choice(fallback_questions)

    # Truncate question if needed to fit SMS limit with prefix and suffix
    prefix = "Quick one: "
    suffix = " Reply or 'skip'"
    max_question_len = SMS_LIMIT - len(prefix) - len(suffix) - 2  # 2 for emoji

    if len(question_text) > max_question_len:
        question_text = question_text[:max_question_len - 3] + "..."

    text = f"{prefix}{question_text}{suffix}"

    return create_sms_content(text)


@router.get("/sms/event-alert/{member_id}/{event_slug}", response_model=SMSContent)
async def get_event_alert_sms(
    member_id: int,
    event_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate SMS text about an event happening soon.

    Includes connection context (friends going).
    """
    member = await get_member_or_404(db, member_id)
    member_name = member.first_name or "Hey"

    # Get connections
    connections = await get_member_connections(db, member_id, limit=2)

    # Mock event title (would come from Rova API)
    event_title = event_slug.replace("-", " ").title()[:30]

    if connections:
        friend_name = connections[0].member_name.split()[0]  # First name only
        text = f"{member_name}, {event_title} is tonight! {friend_name} is going. Join?"
    else:
        text = f"{member_name}, {event_title} is tonight! Looks like your kind of thing. Join?"

    return create_sms_content(text)


@router.get("/sms/connection-nudge/{member_id}", response_model=SMSContent)
async def get_connection_nudge_sms(
    member_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate SMS text about someone they should meet.

    Includes context for the connection.
    """
    member = await get_member_or_404(db, member_id)

    # Get a recent connection
    connections = await get_member_connections(db, member_id, limit=1)

    if connections:
        conn = connections[0]
        first_name = conn.member_name.split()[0]  # First name only

        # Build short context
        if conn.shared_items:
            context = f"You both dig {conn.shared_items[0]}"
        else:
            context = "Great collaboration potential"

        text = f"Meet {first_name}! {context}. Want an intro? Reply 'yes'"
    else:
        # Fallback when no connections
        text = "We're finding your perfect community matches. Complete your profile for better connections!"

    return create_sms_content(text)
