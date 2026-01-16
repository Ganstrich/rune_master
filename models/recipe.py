
"""Recipe/crafting requirement data model."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceRequirement:
    """Single requirement in a recipe: resource_id and quantity.
    
    Immutable to prevent accidental modification of recipes.
    Used in Equipment.recipe to store crafting requirements.
    """
    resource_id: int
    quantity: int
    
    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if self.resource_id < 0:
            raise ValueError(f"resource_id must be positive, got {self.resource_id}")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got {self.quantity}")
    
    def __repr__(self) -> str:
        return f"ResourceRequirement(resource_id={self.resource_id}, qty={self.quantity})"
