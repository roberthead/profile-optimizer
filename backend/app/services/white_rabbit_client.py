"""
Client for fetching member data from the White Rabbit API.

This module provides an async HTTP client for communicating with the
White Rabbit Ashland member API to sync member data.
"""

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhiteRabbitAPIError(Exception):
    """Base exception for White Rabbit API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class WhiteRabbitAuthError(WhiteRabbitAPIError):
    """Raised when authentication fails (401/403)."""

    pass


class WhiteRabbitClient:
    """
    Async HTTP client for the White Rabbit API.

    Usage:
        client = WhiteRabbitClient()
        members = await client.fetch_members()

    Or with custom configuration:
        client = WhiteRabbitClient(
            api_url="https://custom.api.com",
            api_key="your-key"
        )
    """

    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2.0  # Exponential backoff base in seconds

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the White Rabbit API client.

        Args:
            api_url: Base URL for the API. Defaults to settings.WHITE_RABBIT_API_URL.
            api_key: API key for authentication. Defaults to settings.WHITE_RABBIT_API_KEY.
            timeout: Request timeout in seconds. Defaults to 30.
        """
        self.api_url = (api_url or settings.WHITE_RABBIT_API_URL).rstrip("/")
        self.api_key = api_key or settings.WHITE_RABBIT_API_KEY
        self.timeout = timeout

        if not self.api_key:
            raise ValueError(
                "WHITE_RABBIT_API_KEY must be set in environment or passed to constructor"
            )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Any:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., "/members")
            **kwargs: Additional arguments passed to httpx.request

        Returns:
            Parsed JSON response.

        Raises:
            WhiteRabbitAuthError: If authentication fails.
            WhiteRabbitAPIError: For other API errors.
        """
        url = f"{self.api_url}{endpoint}"
        headers = self._get_headers()

        last_exception: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.debug(f"API request: {method} {url} (attempt {attempt + 1})")

                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        **kwargs,
                    )

                    # Handle auth errors (no retry)
                    if response.status_code in (401, 403):
                        logger.error(f"Authentication failed: {response.status_code}")
                        raise WhiteRabbitAuthError(
                            f"Authentication failed: {response.text}",
                            status_code=response.status_code,
                        )

                    # Handle other client errors (no retry)
                    if 400 <= response.status_code < 500:
                        logger.error(
                            f"Client error: {response.status_code} - {response.text}"
                        )
                        raise WhiteRabbitAPIError(
                            f"API error: {response.text}",
                            status_code=response.status_code,
                        )

                    # Handle server errors (retry)
                    if response.status_code >= 500:
                        logger.warning(
                            f"Server error {response.status_code}, attempt {attempt + 1}/{self.MAX_RETRIES}"
                        )
                        last_exception = WhiteRabbitAPIError(
                            f"Server error: {response.text}",
                            status_code=response.status_code,
                        )
                        if attempt < self.MAX_RETRIES - 1:
                            await asyncio.sleep(self.RETRY_BACKOFF_BASE**attempt)
                            continue
                        raise last_exception

                    # Success
                    logger.debug(f"API response: {response.status_code}")
                    return response.json()

            except httpx.TimeoutException as e:
                logger.warning(
                    f"Request timeout, attempt {attempt + 1}/{self.MAX_RETRIES}"
                )
                last_exception = WhiteRabbitAPIError(f"Request timeout: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_BACKOFF_BASE**attempt)
                    continue

            except httpx.RequestError as e:
                logger.warning(
                    f"Request error: {e}, attempt {attempt + 1}/{self.MAX_RETRIES}"
                )
                last_exception = WhiteRabbitAPIError(f"Request failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_BACKOFF_BASE**attempt)
                    continue

        # All retries exhausted
        raise last_exception or WhiteRabbitAPIError("Request failed after all retries")

    async def fetch_members(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Fetch all members from the White Rabbit API.

        Handles pagination automatically to retrieve all members.

        Args:
            limit: Number of members per page (max 50).

        Returns:
            List of member data dictionaries.

        Raises:
            WhiteRabbitAuthError: If authentication fails.
            WhiteRabbitAPIError: For other API errors.
        """
        logger.info("Fetching members from White Rabbit API")

        all_members: list[dict[str, Any]] = []
        page = 0  # API uses 0-indexed pagination
        limit = min(limit, 50)  # API max is 50

        while True:
            response = await self._request(
                "GET",
                "/community/members",
                params={"page": page, "limit": limit},
            )

            # Extract members from response
            if isinstance(response, dict):
                members = response.get("members", response.get("data", []))
                pagination = response.get("pagination", {})
            else:
                members = response if isinstance(response, list) else []
                pagination = {}

            all_members.extend(members)
            logger.debug(f"Fetched page {page}: {len(members)} members")

            # Check if there are more pages
            total_pages = pagination.get("totalPages", 1)
            if page >= total_pages or not members:
                break

            page += 1

        logger.info(f"Fetched {len(all_members)} total members from API")
        return all_members

    async def fetch_member(self, profile_id: str) -> dict[str, Any] | None:
        """
        Fetch a single member by profile ID.

        Args:
            profile_id: The member's profile UUID.

        Returns:
            Member data dictionary, or None if not found.

        Raises:
            WhiteRabbitAuthError: If authentication fails.
            WhiteRabbitAPIError: For other API errors.
        """
        logger.info(f"Fetching member {profile_id} from White Rabbit API")

        try:
            response = await self._request("GET", f"/community/members/{profile_id}")
            # Response may be wrapped in a "member" key
            if isinstance(response, dict) and "member" in response:
                return response["member"]
            return response
        except WhiteRabbitAPIError as e:
            if e.status_code == 404:
                logger.info(f"Member {profile_id} not found")
                return None
            raise

    async def fetch_member_answers(
        self, profile_id: str, source: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch a member's profile question answers.

        Args:
            profile_id: The member's profile UUID.
            source: Optional filter by source (e.g., 'profile_optimizer').

        Returns:
            List of answer dictionaries.

        Raises:
            WhiteRabbitAuthError: If authentication fails.
            WhiteRabbitAPIError: For other API errors.
        """
        logger.info(f"Fetching answers for member {profile_id}")

        params = {}
        if source:
            params["source"] = source

        response = await self._request(
            "GET",
            f"/community/members/{profile_id}/answers",
            params=params if params else None,
        )

        if isinstance(response, dict):
            return response.get("answers", [])
        return response if isinstance(response, list) else []

    async def post_question(self, question_data: dict[str, Any]) -> dict[str, Any]:
        """
        Post a question to the White Rabbit website.

        Args:
            question_data: Question payload with camelCase keys matching the
                White Rabbit API format (questionText, description, questionType,
                source, category, displayOrder, notes).

        Returns:
            Parsed JSON response from the API.

        Raises:
            WhiteRabbitAuthError: If authentication fails.
            WhiteRabbitAPIError: For other API errors.
        """
        logger.info(
            f"Posting question to White Rabbit: {question_data.get('questionText', '')[:50]}"
        )
        return await self._request("POST", "/profile/questions", json=question_data)

    async def health_check(self) -> bool:
        """
        Verify API connectivity and authentication.

        Returns:
            True if the API is reachable and authentication succeeds.

        Raises:
            WhiteRabbitAuthError: If authentication fails.
            WhiteRabbitAPIError: If the API is unreachable.
        """
        logger.info("Performing API health check")

        try:
            # Fetch first page with limit of 1 to minimize data transfer
            await self._request(
                "GET",
                "/community/members",
                params={"page": 1, "limit": 1},
            )
            logger.info("API health check passed")
            return True
        except WhiteRabbitAPIError:
            logger.error("API health check failed")
            raise
