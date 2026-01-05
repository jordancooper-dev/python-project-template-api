"""Tests for middleware and exception handlers."""

import pytest
from httpx import AsyncClient


class TestSecurityHeadersMiddleware:
    """Tests for security headers middleware."""

    @pytest.mark.asyncio
    async def test_security_headers_present(self, client: AsyncClient) -> None:
        """Test that security headers are present in responses."""
        response = await client.get("/health/live")

        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert (
            response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        )
        assert "Content-Security-Policy" in response.headers

    @pytest.mark.asyncio
    async def test_csp_header_content(self, client: AsyncClient) -> None:
        """Test Content-Security-Policy header content."""
        response = await client.get("/health/live")

        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp


class TestCorrelationIdMiddleware:
    """Tests for correlation ID middleware."""

    @pytest.mark.asyncio
    async def test_correlation_id_in_response(self, client: AsyncClient) -> None:
        """Test that correlation ID is returned in response headers."""
        response = await client.get("/health/live")

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        assert len(correlation_id) > 0

    @pytest.mark.asyncio
    async def test_correlation_id_from_request(self, client: AsyncClient) -> None:
        """Test that provided correlation ID is preserved."""
        custom_id = "test-correlation-id-12345"
        response = await client.get(
            "/health/live",
            headers={"X-Correlation-ID": custom_id},
        )

        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == custom_id


class TestRequestLoggingMiddleware:
    """Tests for request logging middleware."""

    @pytest.mark.asyncio
    async def test_process_time_header(self, client: AsyncClient) -> None:
        """Test that X-Process-Time header is present."""
        response = await client.get("/health/live")

        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        # Process time may include 'ms' suffix
        process_time_str = response.headers["X-Process-Time"]
        # Remove 'ms' suffix if present
        process_time_value = process_time_str.replace("ms", "").replace("s", "")
        process_time = float(process_time_value)
        assert process_time >= 0


class TestValidationErrorHandler:
    """Tests for validation error handler."""

    @pytest.mark.asyncio
    async def test_validation_error_format(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test validation error response format."""
        # Send invalid data (empty name)
        response = await authenticated_client.post(
            "/api/v1/items",
            json={"name": "", "description": "test"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "error" in data
        assert data["error"] == "ValidationError"
        assert "correlation_id" in data

    @pytest.mark.asyncio
    async def test_validation_error_has_correlation_id_header(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test validation error has correlation ID in header."""
        response = await authenticated_client.post(
            "/api/v1/items",
            json={"name": ""},
        )

        assert response.status_code == 422
        assert "X-Correlation-ID" in response.headers

    @pytest.mark.asyncio
    async def test_whitespace_only_name_rejected(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test that whitespace-only names are rejected."""
        response = await authenticated_client.post(
            "/api/v1/items",
            json={"name": "   ", "description": "test"},
        )
        # Should be 422 (validation error) - whitespace stripped becomes empty
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestAPIErrorHandler:
    """Tests for API error handler."""

    @pytest.mark.asyncio
    async def test_unauthorized_error_format(self, client: AsyncClient) -> None:
        """Test unauthorized error response format."""
        response = await client.get("/api/v1/items")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_not_found_error(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test not found error response."""
        response = await authenticated_client.get(
            "/api/v1/items/00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == 404


class TestRequestSizeLimitMiddleware:
    """Tests for request size limit middleware."""

    @pytest.mark.asyncio
    async def test_large_request_rejected(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test that requests exceeding size limit are rejected."""
        # Create a payload that would exceed typical limits
        # Note: The actual limit check happens on Content-Length header
        large_description = "x" * (11 * 1024 * 1024)  # 11MB

        response = await authenticated_client.post(
            "/api/v1/items",
            json={"name": "Test", "description": large_description},
            headers={"Content-Length": str(11 * 1024 * 1024)},
        )

        # Should be rejected with 413 Payload Too Large
        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_normal_request_allowed(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test that normal-sized requests are allowed."""
        response = await authenticated_client.post(
            "/api/v1/items",
            json={"name": "Normal Item", "description": "A normal description"},
        )

        assert response.status_code == 201


class TestUUIDValidation:
    """Tests for UUID path parameter validation."""

    @pytest.mark.asyncio
    async def test_invalid_uuid_rejected(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test that invalid UUIDs are rejected."""
        response = await authenticated_client.get("/api/v1/items/not-a-valid-uuid")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_valid_uuid_accepted(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test that valid UUIDs are accepted (even if item doesn't exist)."""
        response = await authenticated_client.get(
            "/api/v1/items/12345678-1234-5678-1234-567812345678"
        )

        # Should be 404 (not found), not 422 (validation error)
        assert response.status_code == 404
