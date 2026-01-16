"""Persistent disk cache for expensive API operations.

Caches:
- Resource information (to avoid re-fetching from API)
- Equipment effects (to avoid re-computing)
- Stat weights (to avoid re-calculating)

Simple JSON-based storage with no special serialization logic.
"""
import os
import json
from typing import Dict, Any, Optional
from config import Config


class CacheManager:
    """Persistent disk-based cache for API data.
    
    Manages JSON cache file to avoid re-fetching data from API.
    Safe for concurrent reads (but not concurrent writes).
    
    Cache structure:
    {
        "resources": {
            "123": {...raw resource data...},
            "456": {...},
        },
        "equipment_effects": {
            "789": [{...effect...}, {...}],
        },
        "stat_weights": {
            "789": 45.5,
        },
        "metadata": {
            "last_update": "2026-01-16T12:30:00",
            "version": "1"
        }
    }
    """
    
    def __init__(self, cache_file: str = Config.CACHE_FILE):
        """Initialize cache manager.
        
        Args:
            cache_file: Path to cache JSON file
        """
        self.cache_file = cache_file
        self._cache: Dict[str, Any] = {}
        self._load_from_disk()
    
    def _load_from_disk(self) -> None:
        """Load cache from disk, or initialize empty if file doesn't exist."""
        if not os.path.exists(self.cache_file):
            self._cache = {
                "resources": {},
                "equipment_effects": {},
                "stat_weights": {},
                "metadata": {"version": "1"}
            }
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure all sections exist
                self._cache = {
                    "resources": data.get("resources", {}),
                    "equipment_effects": data.get("equipment_effects", {}),
                    "stat_weights": data.get("stat_weights", {}),
                    "metadata": data.get("metadata", {"version": "1"})
                }
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Cache file corrupted: {e}. Starting with empty cache.")
            self._cache = {
                "resources": {},
                "equipment_effects": {},
                "stat_weights": {},
                "metadata": {"version": "1"}
            }
    
    def save(self) -> None:
        """Save cache to disk."""
        try:
            os.makedirs(os.path.dirname(self.cache_file) or ".", exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"❌ Failed to save cache: {e}")
    
    # ========================================================================
    # RESOURCE CACHE - Caches raw resource API responses
    # ========================================================================
    
    def get_resource(self, resource_id: int) -> Optional[Dict[str, Any]]:
        """Get cached resource data.
        
        Args:
            resource_id: Resource ID to retrieve
            
        Returns:
            Cached resource dict or None if not cached
        """
        return self._cache["resources"].get(str(resource_id))
    
    def set_resource(self, resource_id: int, data: Dict[str, Any]) -> None:
        """Cache resource data.
        
        Args:
            resource_id: Resource ID
            data: Raw resource data from API
        """
        self._cache["resources"][str(resource_id)] = data
    
    def has_resource(self, resource_id: int) -> bool:
        """Check if resource is cached.
        
        Args:
            resource_id: Resource ID
            
        Returns:
            True if resource is in cache
        """
        return str(resource_id) in self._cache["resources"]
    
    def get_resource_name(self, resource_id: int) -> Optional[str]:
        """Get cached resource name.
        
        Args:
            resource_id: Resource ID
            
        Returns:
            Resource name or None if not cached
        """
        resource = self.get_resource(resource_id)
        if resource:
            return resource.get('name')
        return None
    
    # ========================================================================
    # EQUIPMENT EFFECTS CACHE - Caches equipment effects (expensive to fetch)
    # ========================================================================
    
    def get_equipment_effects(self, equipment_id: int) -> Optional[list]:
        """Get cached equipment effects.
        
        Args:
            equipment_id: Equipment ID
            
        Returns:
            List of effect dicts or None if not cached
        """
        return self._cache["equipment_effects"].get(str(equipment_id))
    
    def set_equipment_effects(self, equipment_id: int, effects: list) -> None:
        """Cache equipment effects.
        
        Args:
            equipment_id: Equipment ID
            effects: List of effect data from API
        """
        self._cache["equipment_effects"][str(equipment_id)] = effects
    
    def has_equipment_effects(self, equipment_id: int) -> bool:
        """Check if equipment effects are cached.
        
        Args:
            equipment_id: Equipment ID
            
        Returns:
            True if effects are in cache
        """
        return str(equipment_id) in self._cache["equipment_effects"]
    
    # ========================================================================
    # STAT WEIGHTS CACHE - Caches computed stat weights
    # ========================================================================
    
    def get_stat_weight(self, equipment_id: int) -> Optional[float]:
        """Get cached stat weight for equipment.
        
        Args:
            equipment_id: Equipment ID
            
        Returns:
            Cached weight or None if not cached
        """
        val = self._cache["stat_weights"].get(str(equipment_id))
        return float(val) if val is not None else None
    
    def set_stat_weight(self, equipment_id: int, weight: float) -> None:
        """Cache computed stat weight.
        
        Args:
            equipment_id: Equipment ID
            weight: Computed weight value
        """
        self._cache["stat_weights"][str(equipment_id)] = float(weight)
    
    def has_stat_weight(self, equipment_id: int) -> bool:
        """Check if stat weight is cached.
        
        Args:
            equipment_id: Equipment ID
            
        Returns:
            True if weight is in cache
        """
        return str(equipment_id) in self._cache["stat_weights"]
    
    # ========================================================================
    # CACHE STATS - Monitoring and debugging
    # ========================================================================
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dict with counts of cached items
        """
        return {
            "cached_resources": len(self._cache["resources"]),
            "cached_effects": len(self._cache["equipment_effects"]),
            "cached_weights": len(self._cache["stat_weights"]),
        }
    
    def clear(self) -> None:
        """Clear all cache (for testing purposes)."""
        self._cache = {
            "resources": {},
            "equipment_effects": {},
            "stat_weights": {},
            "metadata": {"version": "1"}
        }
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"CacheManager("
            f"file={self.cache_file}, "
            f"resources={stats['cached_resources']}, "
            f"effects={stats['cached_effects']}, "
            f"weights={stats['cached_weights']})"
        )
