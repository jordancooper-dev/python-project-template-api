"""Async database session management.

This module provides async database session management with SQLAlchemy 2.0.

Transaction Patterns
--------------------

1. **get_db()** - Auto-commit dependency (most common)
   Use this for standard CRUD operations. The session automatically commits
   on success and rolls back on exception.

   Example::

       @router.post("/items")
       async def create_item(
           db: Annotated[AsyncSession, Depends(get_db)],
           data: ItemCreate,
       ) -> ItemResponse:
           item = Item(**data.model_dump())
           db.add(item)
           # Commit happens automatically after endpoint returns
           return ItemResponse.model_validate(item)

2. **get_db_no_commit()** - Manual transaction control
   Use this when you need explicit control over commits, such as:

   - Multi-step operations where you want to commit partway through
   - Read-only operations where commit overhead is unnecessary
   - Complex transaction logic with savepoints

   Example::

       @router.post("/batch")
       async def batch_operation(
           db: Annotated[AsyncSession, Depends(get_db_no_commit)],
       ) -> dict:
           # Process items in batches with explicit commits
           for batch in batches:
               for item in batch:
                   db.add(item)
               await db.commit()  # Commit each batch
           return {"status": "ok"}
"""

import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_engine() -> AsyncEngine:
    """Get the database engine (lazily initialized).

    Includes connection pool timeout and statement timeout configuration.
    """
    settings = get_settings()
    engine = create_async_engine(
        settings.async_database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        echo=settings.database_echo,
    )

    # Set statement timeout on new connections (PostgreSQL-specific)
    # Note: SET commands don't support parameterized queries in PostgreSQL.
    # The value is an integer from validated settings, so string formatting is safe.
    @event.listens_for(engine.sync_engine, "connect")
    def set_statement_timeout(  # pyright: ignore[reportUnusedFunction]
        dbapi_connection: object, connection_record: object
    ) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        # SET doesn't support parameters, but value is validated integer from settings
        cursor.execute(f"SET statement_timeout = {settings.database_statement_timeout}")
        cursor.close()

    return engine


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the async session factory (lazily initialized)."""
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that provides a database session.

    Yields an async session and handles commit/rollback automatically.
    Use this for standard CRUD operations.
    """
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            raise


async def get_db_no_commit() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that provides a database session without auto-commit.

    Use this when you need manual transaction control, such as:
    - Multi-step operations with intermediate commits
    - Read-only operations
    - Complex transaction logic with savepoints
    """
    async with get_session_factory()() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise


# Module-level aliases for backwards compatibility
# These are functions, not properties - call get_engine() and get_session_factory()
engine = get_engine
async_session_factory = get_session_factory
