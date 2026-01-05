"""Item CRUD service."""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.items.models import Item
from app.items.schemas import ItemCreate, ItemUpdate


class ItemService:
    """Service class for item CRUD operations."""

    @staticmethod
    async def create(db: AsyncSession, data: ItemCreate) -> Item:
        """Create a new item.

        Args:
            db: The database session.
            data: The item creation data.

        Returns:
            The created item.
        """
        item = Item(**data.model_dump())
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item

    @staticmethod
    async def get_by_id(db: AsyncSession, item_id: str) -> Item | None:
        """Get an item by its ID.

        Args:
            db: The database session.
            item_id: The item ID.

        Returns:
            The item if found, None otherwise.
        """
        result = await db.execute(select(Item).where(Item.id == item_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Item], int]:
        """Get all items with pagination.

        Args:
            db: The database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A tuple of (list of items, total count).
        """
        # Get total count
        count_result = await db.execute(select(func.count(Item.id)))
        total = count_result.scalar() or 0

        # Get paginated results
        result = await db.execute(
            select(Item).order_by(Item.created_at.desc()).offset(skip).limit(limit)
        )
        items = list(result.scalars().all())

        return items, total

    # Allowed fields for update - prevents mass assignment vulnerabilities
    _UPDATABLE_FIELDS = frozenset({"name", "description"})

    @staticmethod
    async def update(
        db: AsyncSession,
        item_id: str,
        data: ItemUpdate,
    ) -> Item | None:
        """Update an item.

        Args:
            db: The database session.
            item_id: The item ID.
            data: The update data (only non-None fields are updated).

        Returns:
            The updated item if found, None otherwise.
        """
        item = await ItemService.get_by_id(db, item_id)
        if not item:
            return None

        # Use explicit field mapping to prevent mass assignment vulnerabilities
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data and "name" in ItemService._UPDATABLE_FIELDS:
            item.name = update_data["name"]
        if (
            "description" in update_data
            and "description" in ItemService._UPDATABLE_FIELDS
        ):
            item.description = update_data["description"]

        await db.flush()
        await db.refresh(item)
        return item

    @staticmethod
    async def delete(db: AsyncSession, item_id: str) -> bool:
        """Delete an item.

        Args:
            db: The database session.
            item_id: The item ID.

        Returns:
            True if the item was deleted, False if not found.
        """
        result = await db.execute(delete(Item).where(Item.id == item_id))
        rowcount: int = result.rowcount  # type: ignore[attr-defined]
        return rowcount > 0
