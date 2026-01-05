"""SQLAlchemy declarative base and common model utilities."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def _utc_now() -> datetime:
    """Return current UTC datetime for use as default value."""
    return datetime.now(UTC)


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps.

    Uses UTC timestamps for consistency across environments.
    server_default uses func.now() for database-level defaults (cross-database compatible),
    while onupdate uses Python-side datetime for reliable update tracking.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )
