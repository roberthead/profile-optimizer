from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.agents.interactive import InteractiveAgent
from app.agents.profile_evaluation import ProfileEvaluationAgent
from app.agents.url_processing import UrlProcessingAgent
from app.services.profile_evaluation import ProfileEvaluator
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str

class SocialLinkRequest(BaseModel):
    url: str
    platform: str

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # TODO: Resolve internal member_id from Clerk ID
    # For now, we'll just pass 1 as a dummy member_id if not found
    member_id = 1

    agent = InteractiveAgent(db)
    response = await agent.chat(member_id, request.message, request.session_id)
    return ChatResponse(response=response)

@router.post("/profile/evaluate")
async def evaluate_profile(
    member_id: int = 1,  # TODO: Get from auth when ready
    db: AsyncSession = Depends(get_db)
):
    try:
        evaluator = ProfileEvaluator(db)
        result = await evaluator.evaluate_member(member_id)
        return result
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
