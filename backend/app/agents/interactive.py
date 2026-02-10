from sqlalchemy.ext.asyncio import AsyncSession


class InteractiveAgent:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def chat(self, member_id: int, message: str, session_id: str) -> str:
        """
        Conducts conversation with the member.
        Uses context from Profile Evaluation and URL Artifacts.
        """
        # TODO: Fetch history, context, and call LLM
        return "I am the Interactive Agent. How can I help you optimize your profile?"

    async def _get_context(self, member_id: int) -> str:
        # Fetch profile assessment and artifacts
        return ""
