"""Factory for generating test Item data."""

from typing import Any

from faker import Faker

from app.items.schemas import ItemCreate

fake = Faker()


class ItemFactory:
    """Factory for creating test item data."""

    @staticmethod
    def create_data(**overrides: Any) -> ItemCreate:
        """Create item creation data.

        Args:
            **overrides: Fields to override with specific values.

        Returns:
            ItemCreate schema with test data.
        """
        data: dict[str, Any] = {
            "name": fake.sentence(nb_words=3).rstrip("."),
            "description": fake.paragraph(nb_sentences=2),
        }
        data.update(overrides)
        return ItemCreate(**data)

    @staticmethod
    def create_batch_data(count: int = 3, **overrides: Any) -> list[ItemCreate]:
        """Create multiple item creation data objects.

        Args:
            count: Number of items to create.
            **overrides: Fields to override with specific values.

        Returns:
            List of ItemCreate schemas with test data.
        """
        return [ItemFactory.create_data(**overrides) for _ in range(count)]
