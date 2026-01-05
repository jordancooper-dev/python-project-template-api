"""Tests for items CRUD endpoints."""

import pytest
from httpx import AsyncClient

from tests.factories.items import ItemFactory


@pytest.mark.asyncio
async def test_create_item(authenticated_client: AsyncClient) -> None:
    """Test creating a new item."""
    data = ItemFactory.create_data()

    response = await authenticated_client.post(
        "/api/v1/items",
        json=data.model_dump(),
    )

    assert response.status_code == 201
    result = response.json()
    assert result["name"] == data.name
    assert result["description"] == data.description
    assert "id" in result
    assert "created_at" in result


@pytest.mark.asyncio
async def test_create_item_minimal(authenticated_client: AsyncClient) -> None:
    """Test creating an item with only required fields."""
    response = await authenticated_client.post(
        "/api/v1/items",
        json={"name": "Minimal Item"},
    )

    assert response.status_code == 201
    result = response.json()
    assert result["name"] == "Minimal Item"
    assert result["description"] is None


@pytest.mark.asyncio
async def test_list_items_empty(authenticated_client: AsyncClient) -> None:
    """Test listing items when none exist."""
    response = await authenticated_client.get("/api/v1/items")

    assert response.status_code == 200
    result = response.json()
    assert result["items"] == []
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_list_items_with_data(authenticated_client: AsyncClient) -> None:
    """Test listing items after creating some."""
    # Create items
    for data in ItemFactory.create_batch_data(3):
        await authenticated_client.post("/api/v1/items", json=data.model_dump())

    response = await authenticated_client.get("/api/v1/items")

    assert response.status_code == 200
    result = response.json()
    assert len(result["items"]) == 3
    assert result["total"] == 3


@pytest.mark.asyncio
async def test_list_items_pagination(authenticated_client: AsyncClient) -> None:
    """Test listing items with pagination."""
    # Create 5 items
    for data in ItemFactory.create_batch_data(5):
        await authenticated_client.post("/api/v1/items", json=data.model_dump())

    # Get first page
    response = await authenticated_client.get("/api/v1/items?skip=0&limit=2")

    assert response.status_code == 200
    result = response.json()
    assert len(result["items"]) == 2
    assert result["total"] == 5
    assert result["skip"] == 0
    assert result["limit"] == 2


@pytest.mark.asyncio
async def test_get_item(authenticated_client: AsyncClient) -> None:
    """Test getting a single item by ID."""
    # Create an item
    data = ItemFactory.create_data(name="Test Item")
    create_response = await authenticated_client.post(
        "/api/v1/items",
        json=data.model_dump(),
    )
    item_id = create_response.json()["id"]

    # Get the item
    response = await authenticated_client.get(f"/api/v1/items/{item_id}")

    assert response.status_code == 200
    result = response.json()
    assert result["id"] == item_id
    assert result["name"] == "Test Item"


@pytest.mark.asyncio
async def test_get_item_not_found(authenticated_client: AsyncClient) -> None:
    """Test getting a non-existent item returns 404."""
    response = await authenticated_client.get(
        "/api/v1/items/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_item(authenticated_client: AsyncClient) -> None:
    """Test updating an item."""
    # Create an item
    data = ItemFactory.create_data(name="Original Name")
    create_response = await authenticated_client.post(
        "/api/v1/items",
        json=data.model_dump(),
    )
    item_id = create_response.json()["id"]

    # Update the item
    response = await authenticated_client.patch(
        f"/api/v1/items/{item_id}",
        json={"name": "Updated Name"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["name"] == "Updated Name"
    # Description should be unchanged
    assert result["description"] == data.description


@pytest.mark.asyncio
async def test_update_item_not_found(authenticated_client: AsyncClient) -> None:
    """Test updating a non-existent item returns 404."""
    response = await authenticated_client.patch(
        "/api/v1/items/00000000-0000-0000-0000-000000000000",
        json={"name": "New Name"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_item(authenticated_client: AsyncClient) -> None:
    """Test deleting an item."""
    # Create an item
    data = ItemFactory.create_data()
    create_response = await authenticated_client.post(
        "/api/v1/items",
        json=data.model_dump(),
    )
    item_id = create_response.json()["id"]

    # Delete the item
    response = await authenticated_client.delete(f"/api/v1/items/{item_id}")
    assert response.status_code == 204

    # Verify it's deleted
    get_response = await authenticated_client.get(f"/api/v1/items/{item_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_item_not_found(authenticated_client: AsyncClient) -> None:
    """Test deleting a non-existent item returns 404."""
    response = await authenticated_client.delete(
        "/api/v1/items/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
