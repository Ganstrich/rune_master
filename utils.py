import os
import json
from config import Config
# ==================== CACHE MANAGEMENT ====================
import os
import json
import time
import requests
from functools import lru_cache

class CacheManager:
    _cache = {}
    
    @classmethod
    def initialize(cls):
        """Initialize the cache manager"""
        cls._cache = cls.load_cache()
    
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
    def save_cache():
        """Save resource names to cache file"""
        with open(Config.CACHE_FILE, 'w') as f:
            json.dump(CacheManager._cache, f, indent=2)

    @classmethod
    def get_resource_info(cls, resource_id):
        """Get resource info from cache or API with caching"""
        resource_id_str = str(resource_id)
        
        # Check cache first
        if resource_id_str in cls._cache:
            cached_data = cls._cache[resource_id_str]
            # If we have the full resource info, return it
            if isinstance(cached_data, dict) and 'name' in cached_data:
                return cached_data
            # If we only have the name, we need to fetch the full info
            # This shouldn't happen if we always store full info, but just in case
        
        # If not in cache or incomplete, make API request
        url = f"https://api.dofusdu.de/{Config.GAME}/v1/{Config.LANGUAGE}/items/resources/{resource_id}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                # Update cache with full resource info
                cls._cache[resource_id_str] = data
                return data
        except Exception as e:
            print(f"Error fetching resource {resource_id}: {e}")
        
        return None
    
    @classmethod
    def get_resource_name(cls, resource_id):
        """Get resource name from cache or API with caching"""
        resource_id_str = str(resource_id)
        
        # Check cache first
        if resource_id_str in cls._cache:
            cached_data = cls._cache[resource_id_str]
            # If we have the full resource info, extract the name
            if isinstance(cached_data, dict) and 'name' in cached_data:
                return cached_data['name']
            # If we only have the name as a string, return it
            elif isinstance(cached_data, str):
                return cached_data
        
        # If not in cache, make API request
        url = f"https://api.dofusdu.de/{Config.GAME}/v1/{Config.LANGUAGE}/items/resources/{resource_id}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                name = data.get('name', f"Ressource inconnue ({resource_id})")
                # Update cache with full resource info
                cls._cache[resource_id_str] = data
                return name
        except Exception as e:
            print(f"Error fetching resource {resource_id}: {e}")
        
        return f"Ressource inconnue ({resource_id})"

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
