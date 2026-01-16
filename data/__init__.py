"""Data layer package - API clients, caching, and transformation loaders.

Components:
- api_client: Low-level HTTP communication
- cache_manager: Persistent disk-based caching
- loaders: Transform raw API dicts → dataclasses
"""

from .api_client import DofusAPIClient
from .cache_manager import CacheManager
from .loaders import EquipmentLoader, ResourceLoader

__all__ = [
    "DofusAPIClient",
    "CacheManager",
    "EquipmentLoader",
    "ResourceLoader",
]
