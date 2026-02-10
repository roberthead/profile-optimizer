"""Mobile-optimized API endpoints for swipe-based question interface."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import get_db
from app.models import (
    Question, QuestionDeck, QuestionDelivery, Member, Pattern,
    DeliveryChannel, DeliveryStatus, QuestionVibe,
)

router = APIRouter(prefix="/mobile", tags=["mobile"])


# ============================================================================
# Response Models
# ============================================================================

class MemberContext(BaseModel):
    """Brief member info for question context."""
    id: int
    first_name: Optional[str]
    last_name: Optional[str]

    @property
    def display_name(self) -> str:
        name = " ".join(filter(None, [self.first_name, self.last_name]))
        return name if name else f"Member #{self.id}"


class PatternContext(BaseModel):
    """Brief pattern info for question context."""
    id: int
    name: str
    category: str


class MobileQuestionResponse(BaseModel):
    """Question formatted for mobile swipe interface."""
    id: int
    delivery_id: int
    question_text: str
    question_type: str  # free_form, multiple_choice, yes_no, fill_in_blank
    category: str
    vibe: Optional[str]  # warm, playful, deep, edgy, connector
    difficulty_level: int  # 1-3

    # Type-specific content
    options: List[str]  # For multiple_choice
    blank_prompt: Optional[str]  # For fill_in_blank

    # Context for display
    purpose: str
    notes: Optional[str]  # Why we're asking this
    related_members: List[MemberContext]
    related_pattern: Optional[PatternContext]

    # Progress tracking
    questions_answered_today: int
    questions_remaining: int

    class Config:
        from_attributes = True


class QuestionResponseRequest(BaseModel):
    """Request body for submitting a question response."""
    response_value: str
    response_time_seconds: Optional[int] = None


class QuestionActionResponse(BaseModel):
    """Generic response for question actions."""
    success: bool
    message: str
    next_question_available: bool
    drops_earned: int = 0  # Cafe drops earned from this action
    total_drops: int = 0  # Member's total cafe drops
    streak_days: int = 0  # Current streak


class SessionStatsResponse(BaseModel):
    """Stats about the member's question session."""
    questions_answered_today: int
    questions_skipped_today: int
    questions_saved: int
    current_streak: int
    total_answered: int
    cafe_drops: int = 0  # Total cafe drops
    drops_earned_today: int = 0  # Drops earned today


# ============================================================================
# Helper Functions
# ============================================================================

async def get_or_create_delivery(
    db: AsyncSession,
    question_id: int,
    member_id: int,
    targeting_context: Optional[dict] = None
) -> QuestionDelivery:
    """Get existing delivery or create a new one."""
    # Check for existing pending/delivered
    result = await db.execute(
        select(QuestionDelivery).where(
            and_(
                QuestionDelivery.question_id == question_id,
                QuestionDelivery.member_id == member_id,
                QuestionDelivery.channel == DeliveryChannel.MOBILE_SWIPE,
                QuestionDelivery.delivery_status.in_([
                    DeliveryStatus.PENDING,
                    DeliveryStatus.DELIVERED,
                    DeliveryStatus.VIEWED
                ])
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    # Create new delivery
    delivery = QuestionDelivery(
        question_id=question_id,
        member_id=member_id,
        channel=DeliveryChannel.MOBILE_SWIPE,
        delivery_status=DeliveryStatus.PENDING,
        targeting_context=targeting_context,
    )
    db.add(delivery)
    await db.flush()
    return delivery


async def get_answered_question_ids(db: AsyncSession, member_id: int) -> set:
    """Get IDs of questions this member has already answered or skipped."""
    result = await db.execute(
        select(QuestionDelivery.question_id).where(
            and_(
                QuestionDelivery.member_id == member_id,
                QuestionDelivery.delivery_status.in_([
                    DeliveryStatus.ANSWERED,
                    DeliveryStatus.SKIPPED,
                    DeliveryStatus.EXPIRED
                ])
            )
        )
    )
    return set(row[0] for row in result.all())


async def get_saved_question_ids(db: AsyncSession, member_id: int) -> set:
    """Get IDs of questions saved for later (special response_type)."""
    result = await db.execute(
        select(QuestionDelivery.question_id).where(
            and_(
                QuestionDelivery.member_id == member_id,
                QuestionDelivery.response_type == "saved_for_later"
            )
        )
    )
    return set(row[0] for row in result.all())


async def count_today_actions(db: AsyncSession, member_id: int) -> tuple[int, int]:
    """Count questions answered and skipped today."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    answered = await db.execute(
        select(func.count()).select_from(QuestionDelivery).where(
            and_(
                QuestionDelivery.member_id == member_id,
                QuestionDelivery.delivery_status == DeliveryStatus.ANSWERED,
                QuestionDelivery.answered_at >= today_start
            )
        )
    )
    answered_count = answered.scalar() or 0

    skipped = await db.execute(
        select(func.count()).select_from(QuestionDelivery).where(
            and_(
                QuestionDelivery.member_id == member_id,
                QuestionDelivery.delivery_status == DeliveryStatus.SKIPPED,
                QuestionDelivery.answered_at >= today_start
            )
        )
    )
    skipped_count = skipped.scalar() or 0

    return answered_count, skipped_count


async def get_remaining_questions_count(db: AsyncSession, member_id: int) -> int:
    """Count how many unanswered questions remain for this member."""
    answered_ids = await get_answered_question_ids(db, member_id)

    query = select(func.count()).select_from(Question).where(
        and_(
            Question.is_active == True,
            ~Question.id.in_(answered_ids) if answered_ids else True
        )
    )
    result = await db.execute(query)
    return result.scalar() or 0


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/questions/next", response_model=Optional[MobileQuestionResponse])
async def get_next_question(
    member_id: int = Query(..., description="Member ID to get question for"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the next question for a member in the mobile swipe interface.

    Returns a question optimized for mobile display, with context about
    why the question is being asked and who it relates to.
    """
    # Verify member exists
    member_result = await db.execute(
        select(Member).where(Member.id == member_id)
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Get IDs of already answered/skipped questions
    answered_ids = await get_answered_question_ids(db, member_id)

    # Find next unanswered question
    # Priority: questions targeting this member > personalized deck > global deck
    query = (
        select(Question)
        .join(QuestionDeck, Question.deck_id == QuestionDeck.id)
        .where(
            and_(
                Question.is_active == True,
                QuestionDeck.is_active == True,
                ~Question.id.in_(answered_ids) if answered_ids else True
            )
        )
        .order_by(
            # Prioritize questions with this member in relevant_member_ids
            func.array_position(Question.relevant_member_ids, member_id).nulls_last(),
            # Then by difficulty (easier first for new users)
            Question.difficulty_level,
            # Then by order index
            Question.order_index
        )
        .limit(1)
    )

    result = await db.execute(query)
    question = result.scalar_one_or_none()

    if not question:
        return None

    # Create or get delivery record
    delivery = await get_or_create_delivery(
        db, question.id, member_id,
        targeting_context=question.targeting_criteria
    )

    # Mark as delivered and viewed
    delivery.delivery_status = DeliveryStatus.VIEWED
    delivery.delivered_at = datetime.now(timezone.utc)
    delivery.viewed_at = datetime.now(timezone.utc)

    await db.commit()

    # Get related members for context
    related_members = []
    if question.relevant_member_ids:
        members_result = await db.execute(
            select(Member).where(Member.id.in_(question.relevant_member_ids))
        )
        for m in members_result.scalars().all():
            related_members.append(MemberContext(
                id=m.id,
                first_name=m.first_name,
                last_name=m.last_name
            ))

    # Get related pattern if available
    related_pattern = None
    if question.targeting_criteria and "pattern_id" in question.targeting_criteria:
        pattern_result = await db.execute(
            select(Pattern).where(Pattern.id == question.targeting_criteria["pattern_id"])
        )
        pattern = pattern_result.scalar_one_or_none()
        if pattern:
            related_pattern = PatternContext(
                id=pattern.id,
                name=pattern.name,
                category=pattern.category.value
            )

    # Get stats
    answered_today, _ = await count_today_actions(db, member_id)
    remaining = await get_remaining_questions_count(db, member_id)

    return MobileQuestionResponse(
        id=question.id,
        delivery_id=delivery.id,
        question_text=question.question_text,
        question_type=question.question_type.value,
        category=question.category.value,
        vibe=question.vibe.value if question.vibe else None,
        difficulty_level=question.difficulty_level,
        options=question.options or [],
        blank_prompt=question.blank_prompt,
        purpose=question.purpose,
        notes=question.notes,
        related_members=related_members,
        related_pattern=related_pattern,
        questions_answered_today=answered_today,
        questions_remaining=remaining
    )


@router.post("/questions/{question_id}/respond", response_model=QuestionActionResponse)
async def respond_to_question(
    question_id: int,
    request: QuestionResponseRequest,
    member_id: int = Query(..., description="Member ID responding"),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit an answer to a question.

    For different question types:
    - yes_no: response_value should be "yes" or "no"
    - multiple_choice: response_value should be the selected option text
    - fill_in_blank: response_value is the completed text
    - free_form: response_value is the full text response
    """
    # Get the delivery record
    result = await db.execute(
        select(QuestionDelivery).where(
            and_(
                QuestionDelivery.question_id == question_id,
                QuestionDelivery.member_id == member_id,
                QuestionDelivery.channel == DeliveryChannel.MOBILE_SWIPE,
                QuestionDelivery.delivery_status.in_([
                    DeliveryStatus.DELIVERED,
                    DeliveryStatus.VIEWED
                ])
            )
        )
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(
            status_code=404,
            detail="No active delivery found for this question"
        )

    # Get the question to determine response type
    q_result = await db.execute(
        select(Question).where(Question.id == question_id)
    )
    question = q_result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Update delivery with response
    delivery.delivery_status = DeliveryStatus.ANSWERED
    delivery.answered_at = datetime.now(timezone.utc)
    delivery.response_type = question.question_type.value
    delivery.response_value = request.response_value
    delivery.response_time_seconds = request.response_time_seconds

    # Award cafe drops!
    member_result = await db.execute(select(Member).where(Member.id == member_id))
    member = member_result.scalar_one()

    # Calculate drops earned (base + bonuses)
    drops_earned = 5  # Base drops for answering
    if question.difficulty_level == 2:
        drops_earned += 3  # Bonus for medium questions
    elif question.difficulty_level == 3:
        drops_earned += 7  # Bonus for deep questions

    # Streak bonus
    today = datetime.now(timezone.utc).date()
    if member.last_drop_earned_at:
        last_earned_date = member.last_drop_earned_at.date()
        if last_earned_date == today:
            pass  # Same day, no streak change
        elif (today - last_earned_date).days == 1:
            member.streak_days += 1  # Consecutive day!
            drops_earned += min(member.streak_days, 10)  # Up to 10 bonus for streak
        else:
            member.streak_days = 1  # Streak broken, restart
    else:
        member.streak_days = 1

    # Update member drops
    member.cafe_drops = (member.cafe_drops or 0) + drops_earned
    member.drops_earned_today = (member.drops_earned_today or 0) + drops_earned
    member.last_drop_earned_at = datetime.now(timezone.utc)

    await db.commit()

    # Check if more questions available
    remaining = await get_remaining_questions_count(db, member_id)

    return QuestionActionResponse(
        success=True,
        message="Response recorded successfully",
        next_question_available=remaining > 0,
        drops_earned=drops_earned,
        total_drops=member.cafe_drops,
        streak_days=member.streak_days
    )


@router.post("/questions/{question_id}/skip", response_model=QuestionActionResponse)
async def skip_question(
    question_id: int,
    member_id: int = Query(..., description="Member ID skipping"),
    db: AsyncSession = Depends(get_db)
):
    """
    Skip a question (swipe left / not interested).

    The question won't be shown again to this member.
    """
    # Get or create delivery
    delivery = await get_or_create_delivery(db, question_id, member_id)

    # Mark as skipped
    delivery.delivery_status = DeliveryStatus.SKIPPED
    delivery.answered_at = datetime.now(timezone.utc)
    delivery.response_type = "skip"

    await db.commit()

    remaining = await get_remaining_questions_count(db, member_id)

    return QuestionActionResponse(
        success=True,
        message="Question skipped",
        next_question_available=remaining > 0
    )


@router.post("/questions/{question_id}/save", response_model=QuestionActionResponse)
async def save_question_for_later(
    question_id: int,
    member_id: int = Query(..., description="Member ID saving"),
    db: AsyncSession = Depends(get_db)
):
    """
    Save a question for later (swipe up).

    The question will be moved to the member's saved queue
    and can be accessed from their profile.
    """
    # Get or create delivery
    delivery = await get_or_create_delivery(db, question_id, member_id)

    # Mark as saved (keep as VIEWED so it can still appear, but tag it)
    delivery.response_type = "saved_for_later"

    await db.commit()

    remaining = await get_remaining_questions_count(db, member_id)

    return QuestionActionResponse(
        success=True,
        message="Question saved for later",
        next_question_available=remaining > 0
    )


@router.post("/questions/{question_id}/not-my-vibe", response_model=QuestionActionResponse)
async def mark_not_my_vibe(
    question_id: int,
    member_id: int = Query(..., description="Member ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a question as "not my vibe" (swipe down).

    This provides negative signal that helps refine future questions.
    The question won't be shown again and similar questions may be deprioritized.
    """
    # Get or create delivery
    delivery = await get_or_create_delivery(db, question_id, member_id)

    # Mark with negative signal
    delivery.delivery_status = DeliveryStatus.SKIPPED
    delivery.answered_at = datetime.now(timezone.utc)
    delivery.response_type = "not_my_vibe"

    # Store negative signal in targeting context for future learning
    if delivery.targeting_context is None:
        delivery.targeting_context = {}
    delivery.targeting_context["negative_signal"] = True
    delivery.targeting_context["signal_reason"] = "not_my_vibe"

    await db.commit()

    remaining = await get_remaining_questions_count(db, member_id)

    return QuestionActionResponse(
        success=True,
        message="Thanks for the feedback - we'll adjust future questions",
        next_question_available=remaining > 0
    )


@router.get("/questions/saved", response_model=List[MobileQuestionResponse])
async def get_saved_questions(
    member_id: int = Query(..., description="Member ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get all questions saved for later by this member."""
    saved_ids = await get_saved_question_ids(db, member_id)

    if not saved_ids:
        return []

    result = await db.execute(
        select(Question, QuestionDelivery)
        .join(QuestionDelivery, Question.id == QuestionDelivery.question_id)
        .where(
            and_(
                Question.id.in_(saved_ids),
                QuestionDelivery.member_id == member_id,
                QuestionDelivery.response_type == "saved_for_later"
            )
        )
    )

    questions = []
    answered_today, _ = await count_today_actions(db, member_id)
    remaining = await get_remaining_questions_count(db, member_id)

    for question, delivery in result.all():
        questions.append(MobileQuestionResponse(
            id=question.id,
            delivery_id=delivery.id,
            question_text=question.question_text,
            question_type=question.question_type.value,
            category=question.category.value,
            vibe=question.vibe.value if question.vibe else None,
            difficulty_level=question.difficulty_level,
            options=question.options or [],
            blank_prompt=question.blank_prompt,
            purpose=question.purpose,
            notes=question.notes,
            related_members=[],
            related_pattern=None,
            questions_answered_today=answered_today,
            questions_remaining=remaining
        ))

    return questions


@router.get("/stats", response_model=SessionStatsResponse)
async def get_session_stats(
    member_id: int = Query(..., description="Member ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics about the member's question answering activity."""
    answered_today, skipped_today = await count_today_actions(db, member_id)

    # Count saved
    saved_ids = await get_saved_question_ids(db, member_id)

    # Count total answered
    total_result = await db.execute(
        select(func.count()).select_from(QuestionDelivery).where(
            and_(
                QuestionDelivery.member_id == member_id,
                QuestionDelivery.delivery_status == DeliveryStatus.ANSWERED
            )
        )
    )
    total_answered = total_result.scalar() or 0

    # Get member for drops and streak
    member_result = await db.execute(select(Member).where(Member.id == member_id))
    member = member_result.scalar_one_or_none()

    cafe_drops = member.cafe_drops if member else 0
    drops_earned_today = member.drops_earned_today if member else 0
    current_streak = member.streak_days if member else 0

    return SessionStatsResponse(
        questions_answered_today=answered_today,
        questions_skipped_today=skipped_today,
        questions_saved=len(saved_ids),
        current_streak=current_streak,
        total_answered=total_answered,
        cafe_drops=cafe_drops,
        drops_earned_today=drops_earned_today
    )
