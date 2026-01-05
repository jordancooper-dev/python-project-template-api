"""Item API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import RequireAPIKey
from app.db.session import get_db
from app.items.schemas import ItemCreate, ItemList, ItemResponse, ItemUpdate
from app.items.service import ItemService

router = APIRouter(prefix="/items", tags=["items"])


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an item",
)
async def create_item(
    data: ItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _api_key: RequireAPIKey,
) -> ItemResponse:
    """Create a new item."""
    item = await ItemService.create(db, data)
    return ItemResponse.model_validate(item)


@router.get(
    "",
    response_model=ItemList,
    summary="List items",
)
async def list_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    _api_key: RequireAPIKey,
    skip: int = Query(0, ge=0, le=1000, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum items to return"),
) -> ItemList:
    """List all items with pagination."""
    items, total = await ItemService.get_all(db, skip=skip, limit=limit)
    return ItemList(
        items=[ItemResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get an item",
)
async def get_item(
    item_id: Annotated[UUID, Path(description="The item ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
    _api_key: RequireAPIKey,
) -> ItemResponse:
    """Get an item by ID."""
    item = await ItemService.get_by_id(db, str(item_id))
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    return ItemResponse.model_validate(item)


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update an item",
)
async def update_item(
    item_id: Annotated[UUID, Path(description="The item ID")],
    data: ItemUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _api_key: RequireAPIKey,
) -> ItemResponse:
    """Update an item (partial update)."""
    item = await ItemService.update(db, str(item_id), data)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    return ItemResponse.model_validate(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item",
)
async def delete_item(
    item_id: Annotated[UUID, Path(description="The item ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
    _api_key: RequireAPIKey,
) -> None:
    """Delete an item."""
    deleted = await ItemService.delete(db, str(item_id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
