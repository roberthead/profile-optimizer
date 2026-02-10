import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
import json

security = HTTPBearer()


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Verifies the Clerk JWT token and returns the decoded payload.
    """
    token = credentials.credentials

    if not settings.CLERK_JWKS_URL and not settings.CLERK_ISSUER:
        # Fallback or error if not configured
        # For local dev without auth configured, we might want to bypass or warn
        if not settings.CLERK_PUBLISHABLE_KEY:
            # If no keys are set, maybe we are in a super-dev mode, but better to fail safe
            raise HTTPException(status_code=500, detail="Auth configuration missing")

    jwks_url = (
        settings.CLERK_JWKS_URL or f"{settings.CLERK_ISSUER}/.well-known/jwks.json"
    )

    try:
        # In a real app, cache the JWKS
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            jwks = response.json()

        public_key = RSAAlgorithm.from_jwk(json.dumps(jwks["keys"][0]))

        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=None,  # Clerk tokens often don't have audience or it's specific
            issuer=settings.CLERK_ISSUER,
        )
        return payload
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(payload: dict = Depends(get_current_user_token)) -> str:
    return payload["sub"]
