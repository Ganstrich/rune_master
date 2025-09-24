ALL_CRAFTABLE_TYPES = [
    'ring', 'hat', 'boots', 'belt', 'amulet', 'cloak',
    'shield', 'sword', 'staff', 'hammer', 'wand', 'dagger',
    'bow', 'axe', 'shovel', 'lance', 'scythe']
CORDONNIER = ['boots', 'belt']
BIJOUTIER = ['ring', 'amulet']
TAILLEUR = ['hat', 'cloak']
FORGERON = ['sword', 'hammer', 'dagger', 'axe', 'shovel', 'lance', 'scythe']
SCULPTEUR = ['staff', 'wand', 'bow']
class Config:
    CACHE_FILE = 'resource_cache.json'
    OUTPUT_PREFIX = 'crafting_groups'
    LANGUAGE = 'fr'
    GAME = 'dofus3'
    SORT_BY = 'level'
    SORT_ORDER = 'desc'
    MIN_LEVEL = 100
    MAX_LEVEL = 150
    ITEM_TYPES = CORDONNIER
    FIELDS = ['recipe']
    MIN_COMMON_ITEMS = 3
    MIN_SIMILARITY = 0.3
    MIN_CLUSTER_SIZE = 2
    MIN_SHARING_PERCENTAGE = 60
    EXCLUDED_RESOURCES = {15263, 14635}   # Example resource IDs
