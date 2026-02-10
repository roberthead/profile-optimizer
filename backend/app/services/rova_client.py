"""
Client for fetching event data from the Rova Public API.

This module provides an async HTTP client for communicating with the
Rova events platform API to retrieve events, venues, artists, organizers,
categories, and tags for the Ashland, Oregon community.
"""

import asyncio
import logging
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class RovaAPIError(Exception):
    """Base exception for Rova API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, code: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(self.message)


class RovaAuthError(RovaAPIError):
    """Raised when authentication fails (401/403)."""

    pass


class RovaNotFoundError(RovaAPIError):
    """Raised when a resource is not found (404)."""

    pass


class RovaRateLimitError(RovaAPIError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, status_code=429, code="RATE_LIMIT_EXCEEDED")
        self.retry_after = retry_after


class RovaClient:
    """
    Async HTTP client for the Rova Public API.

    Usage:
        client = RovaClient()
        events = await client.fetch_events(limit=20)

    Or with custom configuration:
        client = RovaClient(
            api_url="https://custom.api.com",
            api_key="your-key"
        )
    """

    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2.0  # Exponential backoff base in seconds

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the Rova API client.

        Args:
            api_url: Base URL for the API. Defaults to settings.ROVA_API_URL.
            api_key: API key for authentication. Defaults to settings.ROVA_API_KEY.
            timeout: Request timeout in seconds. Defaults to 30.
        """
        self.api_url = (api_url or settings.ROVA_API_URL).rstrip("/")
        self.api_key = api_key or settings.ROVA_API_KEY
        self.timeout = timeout

        if not self.api_key:
            import logging
            logging.getLogger(__name__).warning(
                "ROVA_API_KEY not set. Rova API calls will fail. "
                "Set ROVA_API_KEY in environment to enable Rova integration."
            )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "x-api-key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
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
            endpoint: API endpoint path (e.g., "/events")
            **kwargs: Additional arguments passed to httpx.request

        Returns:
            Parsed JSON response.

        Raises:
            RovaAuthError: If authentication fails.
            RovaNotFoundError: If resource is not found.
            RovaRateLimitError: If rate limit is exceeded.
            RovaAPIError: For other API errors.
        """
        url = f"{self.api_url}{endpoint}"
        headers = self._get_headers()

        last_exception: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.debug(f"Rova API request: {method} {url} (attempt {attempt + 1})")

                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        **kwargs,
                    )

                    # Handle auth errors (no retry)
                    if response.status_code in (401, 403):
                        error_data = self._parse_error_response(response)
                        logger.error(f"Rova authentication failed: {response.status_code}")
                        raise RovaAuthError(
                            error_data.get("error", f"Authentication failed: {response.text}"),
                            status_code=response.status_code,
                            code=error_data.get("code"),
                        )

                    # Handle not found (no retry)
                    if response.status_code == 404:
                        error_data = self._parse_error_response(response)
                        logger.info(f"Rova resource not found: {endpoint}")
                        raise RovaNotFoundError(
                            error_data.get("error", "Resource not found"),
                            status_code=404,
                            code=error_data.get("code"),
                        )

                    # Handle rate limiting (retry with backoff)
                    if response.status_code == 429:
                        retry_after = response.headers.get("X-RateLimit-Reset")
                        logger.warning(
                            f"Rova rate limit exceeded, attempt {attempt + 1}/{self.MAX_RETRIES}"
                        )
                        if attempt < self.MAX_RETRIES - 1:
                            wait_time = self.RETRY_BACKOFF_BASE ** attempt
                            await asyncio.sleep(wait_time)
                            continue
                        raise RovaRateLimitError(
                            "Rate limit exceeded",
                            retry_after=int(retry_after) if retry_after else None,
                        )

                    # Handle other client errors (no retry)
                    if 400 <= response.status_code < 500:
                        error_data = self._parse_error_response(response)
                        logger.error(f"Rova client error: {response.status_code} - {response.text}")
                        raise RovaAPIError(
                            error_data.get("error", f"API error: {response.text}"),
                            status_code=response.status_code,
                            code=error_data.get("code"),
                        )

                    # Handle server errors (retry)
                    if response.status_code >= 500:
                        logger.warning(
                            f"Rova server error {response.status_code}, attempt {attempt + 1}/{self.MAX_RETRIES}"
                        )
                        last_exception = RovaAPIError(
                            f"Server error: {response.text}",
                            status_code=response.status_code,
                        )
                        if attempt < self.MAX_RETRIES - 1:
                            await asyncio.sleep(self.RETRY_BACKOFF_BASE ** attempt)
                            continue
                        raise last_exception

                    # Success
                    logger.debug(f"Rova API response: {response.status_code}")
                    return response.json()

            except httpx.TimeoutException as e:
                logger.warning(f"Rova request timeout, attempt {attempt + 1}/{self.MAX_RETRIES}")
                last_exception = RovaAPIError(f"Request timeout: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_BACKOFF_BASE ** attempt)
                    continue

            except httpx.RequestError as e:
                logger.warning(f"Rova request error: {e}, attempt {attempt + 1}/{self.MAX_RETRIES}")
                last_exception = RovaAPIError(f"Request failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_BACKOFF_BASE ** attempt)
                    continue

        # All retries exhausted
        raise last_exception or RovaAPIError("Request failed after all retries")

    def _parse_error_response(self, response: httpx.Response) -> dict[str, Any]:
        """Parse error response from API."""
        try:
            return response.json()
        except Exception:
            return {"error": response.text, "code": None}

    # =========================================================================
    # Events
    # =========================================================================

    async def fetch_events(
        self,
        page: int = 0,
        limit: int = 20,
        sort: Optional[str] = None,
        starts_after: Optional[str] = None,
        starts_before: Optional[str] = None,
        venue_slug: Optional[str] = None,
        venue_id: Optional[str] = None,
        organizer_slug: Optional[str] = None,
        organizer_id: Optional[str] = None,
        artist_slug: Optional[str] = None,
        artist_id: Optional[str] = None,
        category_id: Optional[str] = None,
        area_slug: Optional[str] = None,
        area_id: Optional[str] = None,
        tag: Optional[str] = None,
        tags: Optional[str] = None,
        search: Optional[str] = None,
        featured: Optional[bool] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Fetch paginated list of published events.

        Args:
            page: 0-based page index
            limit: Results per page (max 50)
            sort: Sort order: 'next_occurrence', 'recently_published', 'updated', 'title'
            starts_after: ISO timestamp - only occurrences starting on/after this time
            starts_before: ISO timestamp - only occurrences starting before this time
            venue_slug: Filter by venue slug(s), comma-separated
            venue_id: Filter by venue ID(s), comma-separated
            organizer_slug: Filter by organizer slug(s), comma-separated
            organizer_id: Filter by organizer ID(s), comma-separated
            artist_slug: Filter by artist slug(s), comma-separated
            artist_id: Filter by artist ID(s), comma-separated
            category_id: Filter by category ID(s) - NOTE: no slug support
            area_slug: Filter by area slug(s), comma-separated
            area_id: Filter by area ID(s), comma-separated
            tag: Filter by a single tag value
            tags: Filter by multiple tags (comma-separated)
            search: Full-text search across title, venue, organizer, categories, artists, tags
            featured: True to return only featured events

        Returns:
            Dict with 'events', 'instances', 'count', 'total', 'page', 'limit'
        """
        logger.info("Fetching events from Rova API")

        params: dict[str, Any] = {"page": page, "limit": min(limit, 50)}

        if sort:
            params["sort"] = sort
        if starts_after:
            params["startsAfter"] = starts_after
        if starts_before:
            params["startsBefore"] = starts_before
        if venue_slug:
            params["venueSlug"] = venue_slug
        if venue_id:
            params["venueId"] = venue_id
        if organizer_slug:
            params["organizerSlug"] = organizer_slug
        if organizer_id:
            params["organizerId"] = organizer_id
        if artist_slug:
            params["artistSlug"] = artist_slug
        if artist_id:
            params["artistId"] = artist_id
        if category_id:
            params["categoryId"] = category_id
        if area_slug:
            params["areaSlug"] = area_slug
        if area_id:
            params["areaId"] = area_id
        if tag:
            params["tag"] = tag
        if tags:
            params["tags"] = tags
        if search:
            params["search"] = search
        if featured is not None:
            params["featured"] = str(featured).lower()

        # Add any extra kwargs
        params.update(kwargs)

        response = await self._request("GET", "/events", params=params)
        logger.info(f"Fetched {response.get('count', 0)} events (total: {response.get('total', 0)})")
        return response

    async def fetch_all_events(self, limit: int = 50, **filters: Any) -> list[dict[str, Any]]:
        """
        Fetch all events with automatic pagination.

        Args:
            limit: Page size (max 50)
            **filters: Additional filter parameters

        Returns:
            List of all event objects
        """
        all_events: list[dict[str, Any]] = []
        page = 0

        while True:
            response = await self.fetch_events(page=page, limit=limit, **filters)
            events = response.get("events", [])
            all_events.extend(events)

            total = response.get("total", 0)
            if len(all_events) >= total or not events:
                break

            page += 1

        logger.info(f"Fetched {len(all_events)} total events from Rova API")
        return all_events

    async def fetch_event_by_slug(
        self,
        slug: str,
        instance_id: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None,
        starts_after: Optional[str] = None,
        starts_before: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Fetch full details for a single event by slug.

        Args:
            slug: Event slug identifier
            instance_id: Occurrence key or Neon instance ID for specific occurrence
            date: YYYY-MM-DD format for occurrence lookup
            time: HHMM format for occurrence lookup
            starts_after: ISO timestamp - filter instances window
            starts_before: ISO timestamp - filter instances window

        Returns:
            Dict with 'event', 'instances', optionally 'selectedOccurrence'

        Raises:
            RovaNotFoundError: If event slug not found
        """
        logger.info(f"Fetching event {slug} from Rova API")

        params: dict[str, Any] = {}
        if instance_id:
            params["instanceId"] = instance_id
        if date:
            params["date"] = date
        if time:
            params["time"] = time
        if starts_after:
            params["startsAfter"] = starts_after
        if starts_before:
            params["startsBefore"] = starts_before

        response = await self._request(
            "GET", f"/events/{slug}", params=params if params else None
        )
        return response

    # =========================================================================
    # Venues
    # =========================================================================

    async def fetch_venues(
        self,
        page: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        city: Optional[str] = None,
        with_events: bool = False,
    ) -> dict[str, Any]:
        """
        Fetch paginated venue listing.

        Args:
            page: 0-based page index
            limit: Results per page (max 50)
            search: Search title, street address, city
            city: Exact match on city (case-insensitive)
            with_events: Include upcoming event instances per venue

        Returns:
            Dict with 'venues', 'count', 'total', 'page', 'limit'
        """
        logger.info("Fetching venues from Rova API")

        params: dict[str, Any] = {"page": page, "limit": min(limit, 50)}
        if search:
            params["search"] = search
        if city:
            params["city"] = city
        if with_events:
            params["withEvents"] = "true"

        response = await self._request("GET", "/venues", params=params)
        logger.info(f"Fetched {response.get('count', 0)} venues")
        return response

    async def fetch_venue_by_slug(
        self, slug: str, limit: int = 20
    ) -> dict[str, Any]:
        """
        Fetch single venue with its upcoming events.

        Args:
            slug: Venue slug identifier
            limit: Max events to return (max 20)

        Returns:
            Dict with 'venue', 'events', 'instances', 'count', 'total'

        Raises:
            RovaNotFoundError: If venue slug not found
        """
        logger.info(f"Fetching venue {slug} from Rova API")

        params = {"limit": min(limit, 20)}
        response = await self._request("GET", f"/venues/{slug}", params=params)
        return response

    # =========================================================================
    # Organizers
    # =========================================================================

    async def fetch_organizers(
        self,
        page: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        city: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Fetch paginated organizer listing.

        Args:
            page: 0-based page index
            limit: Results per page (max 50)
            search: Search title, website, address, city, email, phone
            city: Exact match on city (case-insensitive)

        Returns:
            Dict with 'organizers', 'count', 'total', 'page', 'limit'
        """
        logger.info("Fetching organizers from Rova API")

        params: dict[str, Any] = {"page": page, "limit": min(limit, 50)}
        if search:
            params["search"] = search
        if city:
            params["city"] = city

        response = await self._request("GET", "/organizers", params=params)
        logger.info(f"Fetched {response.get('count', 0)} organizers")
        return response

    async def fetch_organizer_by_slug(self, slug: str) -> dict[str, Any]:
        """
        Fetch single organizer by slug.

        Args:
            slug: Organizer slug identifier

        Returns:
            Organizer object

        Raises:
            RovaNotFoundError: If organizer slug not found
        """
        logger.info(f"Fetching organizer {slug} from Rova API")
        # Note: The API docs don't show a dedicated /organizers/{slug} endpoint
        # but we can search for it specifically
        response = await self.fetch_organizers(search=slug, limit=1)
        organizers = response.get("organizers", [])
        if not organizers:
            raise RovaNotFoundError(f"Organizer '{slug}' not found", status_code=404)
        return organizers[0]

    # =========================================================================
    # Artists
    # =========================================================================

    async def fetch_artists(
        self,
        page: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Fetch paginated artist listing.

        Args:
            page: 0-based page index
            limit: Results per page (max 50)
            search: Search title, website, email, tags
            tag: Filter by single tag

        Returns:
            Dict with 'artists', 'count', 'total', 'page', 'limit'
        """
        logger.info("Fetching artists from Rova API")

        params: dict[str, Any] = {"page": page, "limit": min(limit, 50)}
        if search:
            params["search"] = search
        if tag:
            params["tag"] = tag

        response = await self._request("GET", "/artists", params=params)
        logger.info(f"Fetched {response.get('count', 0)} artists")
        return response

    # =========================================================================
    # Categories
    # =========================================================================

    async def fetch_categories(self, search: Optional[str] = None) -> dict[str, Any]:
        """
        Fetch all published categories.

        Args:
            search: Optional filter by title

        Returns:
            Dict with 'categories', 'count', 'total'

        Note:
            Categories do NOT support slug filtering on /events endpoint.
            You must use the 'id' field when filtering events by category.
        """
        logger.info("Fetching categories from Rova API")

        params: dict[str, Any] = {}
        if search:
            params["search"] = search

        response = await self._request(
            "GET", "/categories", params=params if params else None
        )
        logger.info(f"Fetched {response.get('count', 0)} categories")
        return response

    async def fetch_categories_with_tags(self) -> dict[str, Any]:
        """
        Fetch categories with their associated tags from upcoming events.

        Returns:
            Dict with 'categories' (each including 'tags' array)
        """
        logger.info("Fetching categories with tags from Rova API")
        response = await self._request("GET", "/categories/tags")
        return response

    # =========================================================================
    # Areas
    # =========================================================================

    async def fetch_areas(self, search: Optional[str] = None) -> dict[str, Any]:
        """
        Fetch all published geographic areas.

        Args:
            search: Optional filter by title

        Returns:
            Dict with 'areas', 'count', 'total'
        """
        logger.info("Fetching areas from Rova API")

        params: dict[str, Any] = {}
        if search:
            params["search"] = search

        response = await self._request(
            "GET", "/areas", params=params if params else None
        )
        logger.info(f"Fetched {response.get('count', 0)} areas")
        return response

    # =========================================================================
    # Tags
    # =========================================================================

    async def fetch_tags(
        self,
        limit: int = 50,
        starts_after: Optional[str] = None,
        starts_before: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Fetch distinct tags across published events, ordered by usage frequency.

        Args:
            limit: Max tags to return (max 200)
            starts_after: ISO timestamp - only count tags from events in this window
            starts_before: ISO timestamp - only count tags from events in this window

        Returns:
            Dict with 'tags' (each with 'value' and 'usageCount')
        """
        logger.info("Fetching tags from Rova API")

        params: dict[str, Any] = {"limit": min(limit, 200)}
        if starts_after:
            params["startsAfter"] = starts_after
        if starts_before:
            params["startsBefore"] = starts_before

        response = await self._request("GET", "/tags", params=params)
        logger.info(f"Fetched {len(response.get('tags', []))} tags")
        return response

    async def fetch_predefined_tags(self) -> dict[str, Any]:
        """
        Fetch the 17 standardized predefined tags.

        Returns:
            Dict with 'tags' (list of tag strings)
        """
        logger.info("Fetching predefined tags from Rova API")
        response = await self._request("GET", "/tags/predefined")
        return response

    # =========================================================================
    # Overview
    # =========================================================================

    async def fetch_overview(self) -> dict[str, Any]:
        """
        Fetch curated homepage data.

        Returns:
            Dict with 'nextEvent', 'featuredEvent', 'categories' (with events)
        """
        logger.info("Fetching overview from Rova API")
        response = await self._request("GET", "/overview")
        return response

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> bool:
        """
        Verify API connectivity and authentication.

        Returns:
            True if the API is reachable and authentication succeeds.

        Raises:
            RovaAuthError: If authentication fails.
            RovaAPIError: If the API is unreachable.
        """
        logger.info("Performing Rova API health check")

        try:
            # Fetch first page with limit of 1 to minimize data transfer
            await self._request(
                "GET",
                "/events",
                params={"page": 0, "limit": 1},
            )
            logger.info("Rova API health check passed")
            return True
        except RovaAPIError:
            logger.error("Rova API health check failed")
            raise
