"""API key service for key management and validation."""

import logging
import secrets
from datetime import UTC, datetime

import bcrypt
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import APIKey
from app.auth.schemas import APIKeyCreate, APIKeyCreated
from app.config.settings import get_settings
from app.core.middleware import correlation_id_var

logger = logging.getLogger(__name__)


def _get_correlation_id() -> str:
    """Get the current correlation ID for logging."""
    return correlation_id_var.get() or "unknown"


class APIKeyService:
    """Service class for API key operations."""

    KEY_PREFIX = "sk_"
    KEY_LENGTH = 32

    @staticmethod
    def generate_key() -> str:
        """Generate a secure random API key.

        Returns:
            A URL-safe random string prefixed with 'sk_'.
        """
        random_part = secrets.token_urlsafe(APIKeyService.KEY_LENGTH)
        return f"{APIKeyService.KEY_PREFIX}{random_part}"

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key using bcrypt.

        Uses configurable bcrypt rounds from settings for security tuning.

        Args:
            key: The plaintext API key.

        Returns:
            The bcrypt hash of the key.
        """
        settings = get_settings()
        salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
        hashed: bytes = bcrypt.hashpw(key.encode(), salt)
        return hashed.decode()

    @staticmethod
    def verify_key(key: str, key_hash: str) -> bool:
        """Verify an API key against its hash.

        Args:
            key: The plaintext API key.
            key_hash: The stored bcrypt hash.

        Returns:
            True if the key matches the hash.
        """
        result: bool = bcrypt.checkpw(key.encode(), key_hash.encode())
        return result

    @staticmethod
    def get_key_prefix(key: str) -> str:
        """Extract the prefix from an API key for identification.

        Args:
            key: The full API key.

        Returns:
            The first 12 characters of the key.
        """
        return key[:12]

    @staticmethod
    async def create_key(db: AsyncSession, data: APIKeyCreate) -> APIKeyCreated:
        """Create a new API key.

        Args:
            db: The database session.
            data: The key creation data.

        Returns:
            The created key info including the raw key (only shown once).
        """
        raw_key = APIKeyService.generate_key()
        key_hash = APIKeyService.hash_key(raw_key)
        key_prefix = APIKeyService.get_key_prefix(raw_key)

        api_key = APIKey(
            name=data.name,
            client_id=data.client_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            is_active=True,
            expires_at=data.expires_at,
        )

        db.add(api_key)
        await db.flush()
        await db.refresh(api_key)

        logger.info(
            "Created API key",
            extra={
                "key_id": str(api_key.id),
                "key_prefix": key_prefix,
                "client_id": data.client_id,
                "name": data.name,
                "expires_at": str(data.expires_at) if data.expires_at else None,
            },
        )

        return APIKeyCreated(
            id=api_key.id,
            name=api_key.name,
            client_id=api_key.client_id,
            key_prefix=api_key.key_prefix,
            key=raw_key,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
        )

    @staticmethod
    async def validate_key(db: AsyncSession, key: str) -> APIKey | None:
        """Validate an API key and update last_used_at atomically.

        Uses SELECT FOR UPDATE to prevent race conditions when updating
        the last_used_at timestamp. Also checks for key expiration.

        Args:
            db: The database session.
            key: The plaintext API key to validate.

        Returns:
            The APIKey record if valid, None otherwise.
        """
        # Use key prefix for O(1) lookup (unique constraint ensures single match)
        prefix = APIKeyService.get_key_prefix(key)
        correlation_id = _get_correlation_id()

        # Use SELECT FOR UPDATE to lock the row during validation
        # This prevents race conditions when multiple requests validate the same key
        result = await db.execute(
            select(APIKey)
            .where(
                APIKey.is_active == True,  # noqa: E712
                APIKey.key_prefix == prefix,
            )
            .with_for_update(skip_locked=True)
        )

        api_key = result.scalar_one_or_none()
        if api_key is None:
            logger.warning(
                "API key validation failed: key not found or inactive",
                extra={"key_prefix": prefix, "correlation_id": correlation_id},
            )
            return None

        # Verify the key hash
        if not APIKeyService.verify_key(key, api_key.key_hash):
            logger.warning(
                "API key validation failed: hash mismatch",
                extra={"key_prefix": prefix, "correlation_id": correlation_id},
            )
            return None

        # Check if key has expired
        if api_key.is_expired:
            logger.warning(
                "API key validation failed: key expired",
                extra={
                    "key_prefix": prefix,
                    "expires_at": str(api_key.expires_at),
                    "correlation_id": correlation_id,
                },
            )
            return None

        # Update last_used_at atomically (row is already locked)
        api_key.last_used_at = datetime.now(UTC)
        await db.flush()

        logger.debug(
            "API key validated successfully",
            extra={
                "key_id": str(api_key.id),
                "key_prefix": prefix,
                "client_id": api_key.client_id,
                "correlation_id": correlation_id,
            },
        )
        return api_key

    @staticmethod
    async def get_key_by_id(db: AsyncSession, key_id: str) -> APIKey | None:
        """Get an API key by its ID.

        Args:
            db: The database session.
            key_id: The key ID.

        Returns:
            The APIKey record if found.
        """
        result = await db.execute(select(APIKey).where(APIKey.id == key_id))
        return result.scalar_one_or_none()

    # Minimum length for prefix search to prevent overly broad queries
    MIN_PREFIX_LENGTH = 4

    @staticmethod
    async def get_key_by_prefix(db: AsyncSession, prefix: str) -> APIKey | None:
        """Get an API key by its prefix.

        Args:
            db: The database session.
            prefix: The key prefix (minimum 4 characters).

        Returns:
            The APIKey record if found, None if prefix too short or not found.
        """
        # Require minimum prefix length to prevent overly broad searches
        if len(prefix) < APIKeyService.MIN_PREFIX_LENGTH:
            logger.warning(
                "Key prefix search rejected: too short",
                extra={
                    "prefix_length": len(prefix),
                    "min_required": APIKeyService.MIN_PREFIX_LENGTH,
                },
            )
            return None

        result = await db.execute(
            select(APIKey).where(APIKey.key_prefix.startswith(prefix))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_keys(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[APIKey], int]:
        """List all API keys.

        Args:
            db: The database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A tuple of (list of keys, total count).
        """
        # Get total count efficiently (doesn't load all rows)
        count_result = await db.execute(select(func.count(APIKey.id)))
        total = count_result.scalar() or 0

        # Get paginated results
        result = await db.execute(
            select(APIKey).order_by(APIKey.created_at.desc()).offset(skip).limit(limit)
        )
        keys = list(result.scalars().all())

        return keys, total

    @staticmethod
    async def revoke_key(db: AsyncSession, key_id: str) -> bool:
        """Revoke an API key.

        Args:
            db: The database session.
            key_id: The key ID to revoke.

        Returns:
            True if the key was revoked, False if not found.
        """
        result = await db.execute(
            update(APIKey)
            .where(APIKey.id == key_id)
            .values(
                is_active=False,
                revoked_at=datetime.now(UTC),
            )
        )
        rowcount: int = result.rowcount  # type: ignore[attr-defined]
        if rowcount > 0:
            logger.info("Revoked API key", extra={"key_id": key_id})
        return rowcount > 0
