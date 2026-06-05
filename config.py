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
    MIN_LEVEL = 50
    MAX_LEVEL = 100
    ITEM_TYPES = BIJOUTIER + TAILLEUR

    FIELDS = ["recipe", "effects"]
    MIN_COMMON_ITEMS = 3
    MIN_SIMILARITY = 0.3
    MIN_CLUSTER_SIZE = 2
    MIN_SHARING_PERCENTAGE = 60
    EXCLUDED_RESOURCES = {15263, 14635}  # Example resource IDs

    # NEW: Density/Level filtering
    DENSITY_LEVEL_RATIO = 3
    FALLBACK_TO_UNFILTERED = False
    MIN_FILTERED_POOL_SIZE = 10
    MIN_EQUIPMENT_DENSITY = 0.0  # Minimum stat_weight per level (0 = no filter)

    # NEW: Grouping method selection
    GROUPING_METHOD = "hybrid"  # "deterministic", "random", "hybrid"
    RANDOM_GROUP_COUNT = 50
