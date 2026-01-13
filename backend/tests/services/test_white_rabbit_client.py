"""Tests for WhiteRabbitClient."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.white_rabbit_client import (
    WhiteRabbitClient,
    WhiteRabbitAPIError,
    WhiteRabbitAuthError,
)


class TestWhiteRabbitClientInit:
    """Tests for WhiteRabbitClient initialization."""

    def test_requires_api_key(self):
        """Client raises ValueError if no API key is provided."""
        with patch("app.services.white_rabbit_client.settings") as mock_settings:
            mock_settings.WHITE_RABBIT_API_URL = "https://example.com/api"
            mock_settings.WHITE_RABBIT_API_KEY = None

            with pytest.raises(ValueError, match="WHITE_RABBIT_API_KEY must be set"):
                WhiteRabbitClient()

    def test_uses_settings_defaults(self):
        """Client uses settings values by default."""
        with patch("app.services.white_rabbit_client.settings") as mock_settings:
            mock_settings.WHITE_RABBIT_API_URL = "https://example.com/api"
            mock_settings.WHITE_RABBIT_API_KEY = "test-key"

            client = WhiteRabbitClient()

            assert client.api_url == "https://example.com/api"
            assert client.api_key == "test-key"

    def test_accepts_custom_values(self):
        """Client accepts custom API URL and key."""
        client = WhiteRabbitClient(
            api_url="https://custom.com/api/",
            api_key="custom-key",
        )

        assert client.api_url == "https://custom.com/api"  # Trailing slash stripped
        assert client.api_key == "custom-key"

    def test_accepts_custom_timeout(self):
        """Client accepts custom timeout."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
            timeout=60.0,
        )

        assert client.timeout == 60.0


class TestWhiteRabbitClientHeaders:
    """Tests for request headers."""

    def test_includes_bearer_token(self):
        """Headers include Bearer token authorization."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="my-secret-key",
        )

        headers = client._get_headers()

        assert headers["Authorization"] == "Bearer my-secret-key"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


class TestWhiteRabbitClientFetchMembers:
    """Tests for fetch_members method."""

    @pytest.mark.asyncio
    async def test_fetches_from_correct_endpoint(self):
        """Fetches from /community/members endpoint."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "members": [{"profile_id": "123"}],
            "pagination": {"totalPages": 1},
        }

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            await client.fetch_members()

            call_kwargs = mock_request.call_args
            assert "/community/members" in call_kwargs.kwargs["url"]

    @pytest.mark.asyncio
    async def test_handles_pagination(self):
        """Fetches all pages when multiple pages exist."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        # Page 1 response
        page1_response = MagicMock()
        page1_response.status_code = 200
        page1_response.json.return_value = {
            "members": [{"profile_id": "1"}, {"profile_id": "2"}],
            "pagination": {"totalPages": 2, "page": 1},
        }

        # Page 2 response
        page2_response = MagicMock()
        page2_response.status_code = 200
        page2_response.json.return_value = {
            "members": [{"profile_id": "3"}],
            "pagination": {"totalPages": 2, "page": 2},
        }

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = [page1_response, page2_response]

            result = await client.fetch_members()

            assert len(result) == 3
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_handles_data_wrapper(self):
        """Extracts members from 'data' key in response."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"profile_id": "123"}],
            "pagination": {"totalPages": 1},
        }

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await client.fetch_members()

            assert len(result) == 1
            assert result[0]["profile_id"] == "123"

    @pytest.mark.asyncio
    async def test_handles_members_wrapper(self):
        """Extracts members from 'members' key in response."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "members": [{"profile_id": "123"}],
            "pagination": {"totalPages": 1},
        }

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await client.fetch_members()

            assert len(result) == 1


class TestWhiteRabbitClientErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_raises_auth_error_on_401(self):
        """Raises WhiteRabbitAuthError on 401 response."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="bad-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(WhiteRabbitAuthError) as exc_info:
                await client.fetch_members()

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_auth_error_on_403(self):
        """Raises WhiteRabbitAuthError on 403 response."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(WhiteRabbitAuthError) as exc_info:
                await client.fetch_members()

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_raises_api_error_on_404(self):
        """Raises WhiteRabbitAPIError on 404 response."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(WhiteRabbitAPIError) as exc_info:
                await client.fetch_members()

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_retries_on_500_error(self):
        """Retries request on 500 server error."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        # First call fails, second succeeds
        mock_fail_response = MagicMock()
        mock_fail_response.status_code = 500
        mock_fail_response.text = "Internal Server Error"

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = []

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = [mock_fail_response, mock_success_response]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.fetch_members()

            assert result == []
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self):
        """Retries request on timeout."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = []

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = [
                httpx.TimeoutException("Timeout"),
                mock_success_response,
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.fetch_members()

            assert result == []
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Raises error after exhausting retries."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(WhiteRabbitAPIError):
                    await client.fetch_members()

            assert mock_request.call_count == client.MAX_RETRIES


class TestWhiteRabbitClientFetchMember:
    """Tests for fetch_member method."""

    @pytest.mark.asyncio
    async def test_returns_member_data(self):
        """Returns member data for valid profile ID."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "profile_id": "123",
            "email": "test@example.com",
        }

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await client.fetch_member("123")

            assert result["profile_id"] == "123"
            mock_request.assert_called_once()
            # Verify the URL includes the correct path
            call_kwargs = mock_request.call_args
            assert "/community/members/123" in call_kwargs.kwargs["url"]

    @pytest.mark.asyncio
    async def test_unwraps_member_key(self):
        """Extracts member from 'member' wrapper if present."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "member": {"profile_id": "123", "email": "test@example.com"},
        }

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await client.fetch_member("123")

            assert result["profile_id"] == "123"

    @pytest.mark.asyncio
    async def test_returns_none_for_404(self):
        """Returns None when member not found."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await client.fetch_member("nonexistent")

            assert result is None


class TestWhiteRabbitClientFetchMemberAnswers:
    """Tests for fetch_member_answers method."""

    @pytest.mark.asyncio
    async def test_fetches_answers(self):
        """Fetches member answers from correct endpoint."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "answers": [{"question_id": "q1", "answer": "test"}],
        }

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await client.fetch_member_answers("123")

            assert len(result) == 1
            assert result[0]["question_id"] == "q1"
            call_kwargs = mock_request.call_args
            assert "/community/members/123/answers" in call_kwargs.kwargs["url"]

    @pytest.mark.asyncio
    async def test_passes_source_filter(self):
        """Passes source parameter when provided."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"answers": []}

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            await client.fetch_member_answers("123", source="profile_optimizer")

            call_kwargs = mock_request.call_args
            assert call_kwargs.kwargs["params"]["source"] == "profile_optimizer"


class TestWhiteRabbitClientHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        """Returns True when API is reachable."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await client.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_raises_on_auth_failure(self):
        """Raises WhiteRabbitAuthError on authentication failure."""
        client = WhiteRabbitClient(
            api_url="https://example.com",
            api_key="bad-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            with pytest.raises(WhiteRabbitAuthError):
                await client.health_check()
