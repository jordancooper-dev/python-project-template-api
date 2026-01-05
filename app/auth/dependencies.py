"""FastAPI dependencies for API key authentication."""

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import APIKey
from app.auth.service import APIKeyService
from app.config.settings import get_settings
from app.db.session import get_db

# Default API key header name - can be overridden by settings at runtime
_DEFAULT_API_KEY_HEADER = "X-API-Key"

# API key header security scheme - uses default, but validation uses settings
api_key_header = APIKeyHeader(
    name=_DEFAULT_API_KEY_HEADER,
    auto_error=False,
    description="API key for authentication",
)


# Unified error message to prevent user enumeration attacks
_INVALID_API_KEY_MESSAGE = "Invalid API key"


async def get_api_key(
    api_key: Annotated[str | None, Security(api_key_header)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIKey:
    """Validate API key and return the key record.

    Args:
        api_key: The API key from the request header.
        db: The database session.

    Returns:
        The validated APIKey record.

    Raises:
        HTTPException: If the API key is missing or invalid.

    Note:
        Uses a unified error message for all auth failures to prevent
        user enumeration attacks.
    """
    settings = get_settings()

    # Use unified error message for all auth failures
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_API_KEY_MESSAGE,
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check minimum length (fails with same error to prevent enumeration)
    if len(api_key) < settings.api_key_min_length:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_API_KEY_MESSAGE,
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_record = await APIKeyService.validate_key(db, api_key)
    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_API_KEY_MESSAGE,
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return key_record


# Type alias for dependency injection - use this in route functions
RequireAPIKey = Annotated[APIKey, Depends(get_api_key)]
