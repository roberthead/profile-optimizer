from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.agents.interactive import InteractiveAgent
from app.agents.profile_evaluation import ProfileEvaluationAgent
from app.agents.profile_chat import ProfileChatAgent
from app.agents.url_processing import UrlProcessingAgent
from app.agents.question_deck import QuestionDeckAgent
from app.models import Member, ProfileCompleteness, ConversationHistory, QuestionDeck, Question
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta, timezone
import uuid

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    member_id: int

class ChatResponse(BaseModel):
    response: str
    session_id: str
    suggestions_made: List[dict] = []

class SocialLinkRequest(BaseModel):
    url: str
    platform: str

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Chat with the profile optimization agent."""
    try:
        agent = ProfileChatAgent(db)
        result = await agent.chat(
            member_id=request.member_id,
            message=request.message,
            session_id=request.session_id
        )
        return ChatResponse(
            response=result["response"],
            session_id=result["session_id"],
            suggestions_made=result.get("suggestions_made", [])
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]
    session_id: str


@router.get("/chat/history")
async def get_chat_history(
    member_id: int,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get conversation history for a member's session."""
    result = await db.execute(
        select(ConversationHistory)
        .where(ConversationHistory.member_id == member_id)
        .where(ConversationHistory.session_id == session_id)
        .order_by(ConversationHistory.created_at)
    )
    messages = result.scalars().all()

    return ChatHistoryResponse(
        messages=[
            ChatMessage(role=msg.role, content=msg.message_content)
            for msg in messages
        ],
        session_id=session_id
    )


@router.get("/chat/sessions")
async def get_chat_sessions(
    member_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all session IDs for a member, with the most recent message timestamp."""
    # Get distinct sessions with their latest message
    result = await db.execute(
        select(
            ConversationHistory.session_id,
            func.max(ConversationHistory.created_at).label("last_message_at")
        )
        .where(ConversationHistory.member_id == member_id)
        .group_by(ConversationHistory.session_id)
        .order_by(func.max(ConversationHistory.created_at).desc())
    )
    sessions = result.all()

    return {
        "sessions": [
            {"session_id": s.session_id, "last_message_at": s.last_message_at.isoformat()}
            for s in sessions
        ]
    }


@router.post("/profile/evaluate")
async def evaluate_profile(
    member_id: Optional[int] = None,  # TODO: Get from auth when ready
    db: AsyncSession = Depends(get_db)
):
    try:
        # If no member_id provided, get the first available member
        if member_id is None:
            result = await db.execute(
                select(Member.id).order_by(Member.id).limit(1)
            )
            member_id = result.scalar_one_or_none()
            if member_id is None:
                raise HTTPException(status_code=404, detail="No members found")

        # Check for existing recent evaluation
        one_week_ago = datetime.now(timezone.utc) - timedelta(weeks=1)
        result = await db.execute(
            select(ProfileCompleteness).where(ProfileCompleteness.member_id == member_id)
        )
        existing = result.scalar_one_or_none()

        # Use cached result if it exists and is less than a week old
        if existing and existing.last_calculated and existing.last_calculated >= one_week_ago:
            missing_fields = existing.missing_fields or {}
            return {
                "completeness_score": existing.completeness_score,
                "missing_fields": missing_fields.get("required", []),
                "optional_missing": missing_fields.get("optional", []),
                "assessment": existing.assessment or "",
                "last_calculated": existing.last_calculated.isoformat() if existing.last_calculated else None,
            }

        # Otherwise, run the agent to generate a fresh evaluation
        agent = ProfileEvaluationAgent(db)
        result = await agent.evaluate_profile(member_id)

        # Return in the format expected by the frontend
        return {
            "completeness_score": result["completeness_score"],
            "missing_fields": [f for f in result["empty_fields"] if f in ["First Name", "Last Name", "Email"]],
            "optional_missing": [f for f in result["empty_fields"] if f not in ["First Name", "Last Name", "Email"]],
            "assessment": result.get("assessment", ""),
            "last_calculated": result.get("last_calculated", None),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/social-links")
async def add_social_link(
    link: SocialLinkRequest,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    member_id = 1 # TODO: Resolve

    # Save link to DB (Pseudo-code)
    # social_link = SocialLink(member_id=member_id, url=link.url, platform=link.platform)
    # db.add(social_link)
    # await db.commit()

    # Trigger background processing
    agent = UrlProcessingAgent(db)
    # background_tasks.add_task(agent.process_url, social_link.id)

    return {"status": "processing", "message": "Link added and processing started"}


# Member endpoints
class MemberSummary(BaseModel):
    id: int
    profile_id: str
    first_name: Optional[str]
    last_name: Optional[str]
    email: str
    membership_status: str
    location: Optional[str]
    role: Optional[str]
    skills_count: int
    interests_count: int

    class Config:
        from_attributes = True


class MemberDetail(BaseModel):
    id: int
    profile_id: str
    clerk_user_id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    bio: Optional[str]
    company: Optional[str]
    role: Optional[str]
    website: Optional[str]
    location: Optional[str]
    membership_status: str
    is_public: bool
    urls: List[str]
    roles: List[str]
    prompt_responses: List[str]
    skills: List[str]
    interests: List[str]
    all_traits: List[str]

    class Config:
        from_attributes = True


class MembersListResponse(BaseModel):
    members: List[MemberSummary]
    total: int
    page: int
    per_page: int
    total_pages: int


@router.get("/members", response_model=MembersListResponse)
async def list_members(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    membership_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all members with pagination and optional filtering."""
    query = select(Member)

    # Always exclude cancelled and expired members
    query = query.where(Member.membership_status.notin_(['cancelled', 'expired']))

    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Member.first_name.ilike(search_pattern)) |
            (Member.last_name.ilike(search_pattern)) |
            (Member.email.ilike(search_pattern)) |
            (Member.bio.ilike(search_pattern))
        )

    if membership_status:
        query = query.where(Member.membership_status == membership_status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.order_by(Member.last_name.asc().nulls_last(), Member.first_name.asc().nulls_last())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    members = result.scalars().all()

    return MembersListResponse(
        members=[
            MemberSummary(
                id=m.id,
                profile_id=str(m.profile_id),
                first_name=m.first_name,
                last_name=m.last_name,
                email=m.email,
                membership_status=m.membership_status,
                location=m.location,
                role=m.role,
                skills_count=len(m.skills) if m.skills else 0,
                interests_count=len(m.interests) if m.interests else 0,
            )
            for m in members
        ],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page if total > 0 else 1,
    )


@router.get("/members/{member_id}", response_model=MemberDetail)
async def get_member(
    member_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a single member by ID."""
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    return MemberDetail(
        id=member.id,
        profile_id=str(member.profile_id),
        clerk_user_id=member.clerk_user_id,
        email=member.email,
        first_name=member.first_name,
        last_name=member.last_name,
        bio=member.bio,
        company=member.company,
        role=member.role,
        website=member.website,
        location=member.location,
        membership_status=member.membership_status,
        is_public=member.is_public,
        urls=member.urls or [],
        roles=member.roles or [],
        prompt_responses=member.prompt_responses or [],
        skills=member.skills or [],
        interests=member.interests or [],
        all_traits=member.all_traits or [],
    )


# Question Deck endpoints
class GenerateGlobalDeckRequest(BaseModel):
    deck_name: str = "Community Discovery Deck"
    num_questions: int = 20
    focus_categories: Optional[List[str]] = None


class GeneratePersonalDeckRequest(BaseModel):
    member_id: int
    num_questions: int = 10


class RefineDeckRequest(BaseModel):
    deck_id: int
    feedback: str


class QuestionModel(BaseModel):
    id: int
    question_text: str
    category: str
    difficulty_level: int
    purpose: str
    follow_up_prompts: List[str]
    potential_insights: List[str]
    related_profile_fields: List[str]

    class Config:
        from_attributes = True


class QuestionDeckModel(BaseModel):
    id: int
    deck_id: str
    name: str
    description: Optional[str]
    member_id: Optional[int]
    is_active: bool
    version: int
    questions: List[QuestionModel]
    created_at: datetime

    class Config:
        from_attributes = True


class DeckGenerationResponse(BaseModel):
    success: bool
    deck_id: Optional[int]
    questions_generated: int
    response_text: str


@router.post("/questions/deck/generate-global", response_model=DeckGenerationResponse)
async def generate_global_deck(
    request: GenerateGlobalDeckRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate a global question deck by analyzing all member profiles."""
    agent = QuestionDeckAgent(db)
    result = await agent.generate_global_deck(
        deck_name=request.deck_name,
        num_questions=request.num_questions,
        focus_categories=request.focus_categories
    )
    return DeckGenerationResponse(**result)


@router.post("/questions/deck/generate-personal", response_model=DeckGenerationResponse)
async def generate_personal_deck(
    request: GeneratePersonalDeckRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate a personalized question deck for a specific member."""
    try:
        agent = QuestionDeckAgent(db)
        result = await agent.generate_personalized_deck(
            member_id=request.member_id,
            num_questions=request.num_questions
        )
        return DeckGenerationResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/questions/deck/refine", response_model=DeckGenerationResponse)
async def refine_deck(
    request: RefineDeckRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refine an existing question deck based on feedback."""
    try:
        agent = QuestionDeckAgent(db)
        result = await agent.refine_deck(
            deck_id=request.deck_id,
            feedback=request.feedback
        )
        return DeckGenerationResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/questions/decks", response_model=List[QuestionDeckModel])
async def list_decks(
    member_id: Optional[int] = None,
    include_global: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List question decks, optionally filtered by member."""
    query = select(QuestionDeck).where(QuestionDeck.is_active == True)

    if member_id is not None:
        if include_global:
            query = query.where(
                (QuestionDeck.member_id == member_id) |
                (QuestionDeck.member_id.is_(None))
            )
        else:
            query = query.where(QuestionDeck.member_id == member_id)
    elif not include_global:
        query = query.where(QuestionDeck.member_id.isnot(None))

    query = query.order_by(QuestionDeck.created_at.desc())

    result = await db.execute(query)
    decks = result.scalars().all()

    # Load questions for each deck
    response_decks = []
    for deck in decks:
        questions_result = await db.execute(
            select(Question)
            .where(Question.deck_id == deck.id)
            .where(Question.is_active == True)
            .order_by(Question.order_index)
        )
        questions = questions_result.scalars().all()

        response_decks.append(QuestionDeckModel(
            id=deck.id,
            deck_id=str(deck.deck_id),
            name=deck.name,
            description=deck.description,
            member_id=deck.member_id,
            is_active=deck.is_active,
            version=deck.version,
            questions=[
                QuestionModel(
                    id=q.id,
                    question_text=q.question_text,
                    category=q.category.value,
                    difficulty_level=q.difficulty_level,
                    purpose=q.purpose,
                    follow_up_prompts=q.follow_up_prompts or [],
                    potential_insights=q.potential_insights or [],
                    related_profile_fields=q.related_profile_fields or [],
                )
                for q in questions
            ],
            created_at=deck.created_at,
        ))

    return response_decks


@router.get("/questions/deck/{deck_id}", response_model=QuestionDeckModel)
async def get_deck(
    deck_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific question deck with its questions."""
    result = await db.execute(
        select(QuestionDeck).where(QuestionDeck.id == deck_id)
    )
    deck = result.scalar_one_or_none()

    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    questions_result = await db.execute(
        select(Question)
        .where(Question.deck_id == deck.id)
        .where(Question.is_active == True)
        .order_by(Question.order_index)
    )
    questions = questions_result.scalars().all()

    return QuestionDeckModel(
        id=deck.id,
        deck_id=str(deck.deck_id),
        name=deck.name,
        description=deck.description,
        member_id=deck.member_id,
        is_active=deck.is_active,
        version=deck.version,
        questions=[
            QuestionModel(
                id=q.id,
                question_text=q.question_text,
                category=q.category.value,
                difficulty_level=q.difficulty_level,
                purpose=q.purpose,
                follow_up_prompts=q.follow_up_prompts or [],
                potential_insights=q.potential_insights or [],
                related_profile_fields=q.related_profile_fields or [],
            )
            for q in questions
        ],
        created_at=deck.created_at,
    )
