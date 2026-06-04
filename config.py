"""API-level configuration only.

Processing pipeline configuration lives in processing.config_dataclass.ProcessingConfig.
"""

ALL_CRAFTABLE_TYPES = [
    "ring",
    "hat",
    "boots",
    "belt",
    "amulet",
    "cloak",
    "shield",
    "sword",
    "staff",
    "hammer",
    "wand",
    "dagger",
    "bow",
    "axe",
    "shovel",
    "lance",
    "scythe",
]
CORDONNIER = ["boots", "belt"]
BIJOUTIER = ["ring", "amulet"]
TAILLEUR = ["hat", "cloak"]
FORGERON = ["sword", "hammer", "dagger", "axe", "shovel", "lance", "scythe"]
SCULPTEUR = ["staff", "wand", "bow"]
FACONNEUR = ["shield"]


class Config:
    CACHE_FILE = "resource_cache.db"
    OUTPUT_PREFIX = "crafting_groups"
    LANGUAGE = "fr"
    GAME = "dofus3"
    SORT_BY = "level"
    SORT_ORDER = "desc"
    MIN_LEVEL = 20
    MAX_LEVEL = 90
    ITEM_TYPES = BIJOUTIER + FORGERON

    FIELDS = ["recipe", "effects"]
