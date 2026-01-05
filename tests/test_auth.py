"""Tests for API key authentication."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import APIKey
from app.auth.service import APIKeyService


@pytest.mark.asyncio
async def test_api_key_generation() -> None:
    """Test API key generation produces valid keys."""
    key = APIKeyService.generate_key()

    assert key.startswith("sk_")
    assert len(key) >= 32


@pytest.mark.asyncio
async def test_api_key_hashing() -> None:
    """Test API key hashing and verification."""
    key = APIKeyService.generate_key()
    hashed = APIKeyService.hash_key(key)

    assert hashed != key
    assert APIKeyService.verify_key(key, hashed)
    assert not APIKeyService.verify_key("wrong_key", hashed)


@pytest.mark.asyncio
async def test_request_without_api_key(client: AsyncClient) -> None:
    """Test that requests without API key return 401."""
    response = await client.get("/api/v1/items")

    assert response.status_code == 401
    # Unified error message prevents user enumeration
    assert "Invalid API key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_request_with_invalid_api_key(client: AsyncClient) -> None:
    """Test that requests with invalid API key return 401."""
    client.headers["X-API-Key"] = "sk_invalid_key_that_does_not_exist"
    response = await client.get("/api/v1/items")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_request_with_valid_api_key(
    authenticated_client: AsyncClient,
) -> None:
    """Test that requests with valid API key succeed."""
    response = await authenticated_client.get("/api/v1/items")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_key_last_used_updated(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    test_api_key: tuple[str, APIKey],
) -> None:
    """Test that last_used_at is updated after API key use."""
    _, api_key = test_api_key

    # Make a request
    await authenticated_client.get("/api/v1/items")

    # Refresh the key from database
    await db_session.refresh(api_key)

    assert api_key.last_used_at is not None


@pytest.mark.asyncio
async def test_revoked_api_key_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    test_api_key: tuple[str, APIKey],
) -> None:
    """Test that revoked API keys are rejected."""
    raw_key, api_key = test_api_key

    # Revoke the key
    await APIKeyService.revoke_key(db_session, api_key.id)
    await db_session.commit()

    # Try to use the revoked key
    client.headers["X-API-Key"] = raw_key
    response = await client.get("/api/v1/items")

    assert response.status_code == 401
