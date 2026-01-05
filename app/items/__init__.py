"""Items module - CRUD example domain."""

from app.items.models import Item
from app.items.router import router

__all__ = ["Item", "router"]
