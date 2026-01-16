from typing import TypedDict, Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class ImageURLs(TypedDict):
    icon: str
    sd: str


class ItemType(TypedDict):
    name: str
    id: int


class StatType(TypedDict):
    """Represents a stat type with id and name."""
    name: str
    id: int


# Mapping table: stat_id -> stat_name
STAT_ID_TO_NAME = {
    9: 'Vitalité',
    10: 'Sagesse',
    25: 'Prospection',
    29: '% Critique',
    38: 'Dommage Critiques',
    59: 'Fuite',
    121: 'Soin',
    63: '% Résistance Terre',
    17: '% Résistance Eau',
    16: '% Résistance Air',
    31: 'Portée',
    46: 'Résistance Critiques',
}


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

class StatWeight(Enum):
    PA = 100.0
    PM = 90.0
    Portée = 51.0
    Invocation = 30.0
    Dommage = 20.0
    Vitalité = 0.2
    Pods = 0.25
    Initiative = 0.1
    Force = 1.0
    Intelligence = 1.0
    Chance = 1.0
    Agilité = 1.0
    Sagesse = 3.0
    Prospection = 0.5


@dataclass
class EquipmentStat:
    """Represents an equipment effect/stat with all metadata from API."""
    stat_type: StatType
    int_minimum: int
    int_maximum: int
    ignore_int_min: bool = False
    ignore_int_max: bool = False
    formatted: str = ""
    
    @property
    def stat_name(self) -> str:
        """Get the stat name."""
        return self.stat_type['name']
    
    @property
    def stat_id(self) -> int:
        """Get the stat id."""
        return self.stat_type['id']
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EquipmentStat':
        """Convert raw API data to EquipmentStat."""
        return cls(
            stat_type=StatType(data.get('type')),
            int_minimum=data.get('int_minimum', 0),
            int_maximum=data.get('int_maximum', 0),
            ignore_int_min=data.get('ignore_int_min', False),
            ignore_int_max=data.get('ignore_int_max', False),
            formatted=data.get('formatted', '')
        )

@dataclass
class Equipment:
    ankama_id: int
    type: ItemType
    level: int
    name: str
    effects: List[EquipmentStat] = field(default_factory=list)
    stat_weight: Optional[float] = None
    recipe: List[ResourceRequirement] = field(default_factory=list)
    image_urls: Optional[ImageURLs] = None

    @staticmethod
    def get_effects(ankama_id) -> List[EquipmentStat]:
        from dofusapi import DofusAPI
        effects = DofusAPI().get_equipment_info(ankama_id).get('effects', [])
        return [EquipmentStat.from_dict(effect) for effect in effects]
    
    @staticmethod
    def compute_stat_weight(effects: List[EquipmentStat]) -> float:
        weight = 0.0
        for effect in effects:
            # Example weight calculation: average of min and max values
            avg_value = (effect.int_minimum + effect.int_maximum) / 2
            
            weight += avg_value  # You can customize the weight calculation as needed
        return weight

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

        effects = Equipment.get_effects(int(raw.get("ankama_id")))

        return cls(
            ankama_id=int(raw.get("ankama_id")),
            type=ItemType(raw.get("type")),
            name=raw.get("name"),
            level=int(raw.get("level")),
            image_urls=ImageURLs(dict(raw.get("image_urls"))),
            effects=effects,
            recipe=reqs,
        )
