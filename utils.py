import os
import json
from config import Config
# ==================== CACHE MANAGEMENT ====================
class CacheManager:
    @staticmethod
    def load_cache():
        """Load resource names from cache file if it exists"""
        if os.path.exists(Config.CACHE_FILE):
            try:
                with open(Config.CACHE_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    @staticmethod
    def save_cache(cache):
        """Save resource names to cache file"""
        with open(Config.CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)

# ==================== EXCLUSION MANAGEMENT ====================
class ExclusionManager:
    @staticmethod
    def load_exclusions():
        """Charger la liste des objets à exclure"""
        exclusion_file = 'excluded_items.txt'
        exclusions = set()
        
        if os.path.exists(exclusion_file):
            with open(exclusion_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        exclusions.add(line)
        
        return exclusions

    @staticmethod
    def filter_equipments(equipments, exclusions):
        """Filtrer les équipements à exclure"""
        filtered = []
        for eq in equipments:
            if eq['name'] not in exclusions:
                filtered.append(eq)
            else:
                print(f"Équipement exclu: {eq['name']}")
        return filtered
