
"""Resource data model."""
from typing import Optional
from dataclasses import dataclass

from .common import ImageURLs, ItemType


@dataclass(frozen=True)
class Resource:
    """Resource data model.
    
    Immutable dataclass representing a crafting resource (ingredient).
    Pure data container - no API calls, no transformations.
    All business logic (loading, transformations) goes to loaders.py
    """
    ankama_id: int
    name: str
    description: str
    type: ItemType
    level: int
    pods: int
    image_urls: Optional[ImageURLs] = None
    
    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if self.ankama_id < 0:
            raise ValueError(f"ankama_id must be positive, got {self.ankama_id}")
        if self.level < 0:
            raise ValueError(f"level must be positive, got {self.level}")
        if self.pods < 0:
            raise ValueError(f"pods must be positive, got {self.pods}")
    
    def __repr__(self) -> str:
        return (
            f"Resource("
            f"id={self.ankama_id}, "
            f"name={self.name}, "
            f"level={self.level}, "
            f"pods={self.pods})"
        )
