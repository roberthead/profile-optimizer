from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pathlib import Path

# Get the project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    PROJECT_NAME: str = "White Rabbit Profile Optimizer"
    API_V1_STR: str = "/api/v1"

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "profile_optimizer"
    DATABASE_URL: Optional[str] = None

    # Auth (Clerk)
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_SECRET_KEY: Optional[str] = None
    CLERK_ISSUER: Optional[str] = None # e.g. https://clerk.whiterabbit.com
    CLERK_JWKS_URL: Optional[str] = None # Auto-derived usually, but good to have

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []

    # AI
    ANTHROPIC_API_KEY: Optional[str] = None

    # White Rabbit API
    WHITE_RABBIT_API_URL: str = "https://whiterabbitashland.com/api"
    WHITE_RABBIT_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), case_sensitive=True)

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

settings = Settings()
