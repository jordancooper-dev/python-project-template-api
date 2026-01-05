"""Factory for generating test API key data."""

from typing import Any

from faker import Faker

from app.auth.schemas import APIKeyCreate

fake = Faker()


class APIKeyFactory:
    """Factory for creating test API key data."""

    @staticmethod
    def create_data(**overrides: Any) -> APIKeyCreate:
        """Create API key creation data.

        Args:
            **overrides: Fields to override with specific values.

        Returns:
            APIKeyCreate schema with test data.
        """
        data: dict[str, Any] = {
            "name": f"{fake.company()} API Key",
            "client_id": fake.uuid4(),
        }
        data.update(overrides)
        return APIKeyCreate(**data)

    @staticmethod
    def create_batch_data(count: int = 3, **overrides: Any) -> list[APIKeyCreate]:
        """Create multiple API key creation data objects.

        Args:
            count: Number of keys to create.
            **overrides: Fields to override with specific values.

        Returns:
            List of APIKeyCreate schemas with test data.
        """
        return [APIKeyFactory.create_data(**overrides) for _ in range(count)]
