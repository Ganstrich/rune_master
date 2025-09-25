from typing import TypedDict, Dict, Any, Optional, List
from dataclasses import dataclass, field


class ImageURLs(TypedDict):
    icon: str
    sd: str


class ItemType(TypedDict):
    name: str
    id: int


@dataclass(frozen=True)
class ResourceRequirement:
    resource_id: int
    quantity: int


@dataclass(frozen=True)
class Resource:
    ankama_id: int
    name: str
    description: str
    type: ItemType
    level: int
    pods: int
    image_urls: Optional[ImageURLs] = None

    @classmethod
    def from_raw(cls, raw: dict) -> "Resource":
        """Convert a raw resource dict from DofusAPI into a Resource dataclass."""
        return cls(
            ankama_id=int(raw.get("ankama_id")),
            name=raw.get("name"),
            description=raw.get("description"),
            type=ItemType(raw.get("type")),
            level=int(raw.get("level")),
            pods=int(raw.get("pods")),
            image_urls=ImageURLs(dict(raw.get("image_urls"))),
        )


@dataclass
class Equipment:
    ankama_id: int
    type: ItemType
    level: int
    name: str
    recipe: List[ResourceRequirement] = field(default_factory=list)
    image_urls: Optional[ImageURLs] = None

    @classmethod
    def from_raw(cls, raw: dict) -> "Equipment":
        """
        Convert a raw equipment dict from DofusAPI into an Equipment dataclass.
        Expects 'recipe' to be a list of RawRecipeItem-like dicts.
        """
        # Parse recipe (filter only resources)
        recipe_raw = raw.get("recipe", []) or []
        reqs: List[ResourceRequirement] = [
            ResourceRequirement(
                resource_id=int(item["item_ankama_id"]), quantity=int(item["quantity"])
            )
            for item in recipe_raw
            if isinstance(item, dict) and item.get("item_subtype") == "resources"
        ]

        return cls(
            ankama_id=int(raw.get("ankama_id")),
            type=ItemType(raw.get("type")),
            name=raw.get("name"),
            level=int(raw.get("level")),
            image_urls=ImageURLs(dict(raw.get("image_urls"))),
            recipe=reqs,
        )
