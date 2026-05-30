"""Transformation layer: raw API dicts → dataclasses with intelligent caching.

This module implements the "from_raw" pattern for all data models.
Loaders handle:
- Converting raw API dicts to dataclasses
- Computing derived values (e.g., stat weights)
- Caching expensive transformations
- Enriching data with cache lookups

No business logic here - just transformations.
"""
from typing import List, Dict, Any, Optional
from models import Equipment, EquipmentStat, Resource, ResourceRequirement
from models import StatType, ItemType, ImageURLs
from .api_client import DofusAPIClient
from .cache_manager import CacheManager
from processing.stat_calculator import calculate_equipment_weight


class EquipmentLoader:
    """Transform raw equipment API responses → Equipment dataclasses."""
    
    def __init__(self, cache: Optional[CacheManager] = None):
        """Initialize loader.
        
        Args:
            cache: CacheManager instance for caching effects/weights
        """
        self.cache = cache or CacheManager()
    
    @staticmethod
    def _parse_effects(effects_data: List[Dict[str, Any]]) -> List[EquipmentStat]:
        """Convert raw effect dicts to EquipmentStat objects.
        
        Args:
            effects_data: List of raw effect dicts from API
            
        Returns:
            List of EquipmentStat objects
        """
        stats = []
        for effect_raw in effects_data:
            try:
                stat = EquipmentStat(
                    stat_type=StatType(effect_raw.get('type', {})),
                    int_minimum=int(effect_raw.get('int_minimum', 0)),
                    int_maximum=int(effect_raw.get('int_maximum', 0)),
                    ignore_int_min=bool(effect_raw.get('ignore_int_min', False)),
                    ignore_int_max=bool(effect_raw.get('ignore_int_max', False)),
                    formatted=str(effect_raw.get('formatted', ''))
                )
                stats.append(stat)
            except (KeyError, ValueError, TypeError) as e:
                print(f"⚠️  Failed to parse effect: {e}")
                continue
        return stats
    
    @staticmethod
    def _parse_recipe(recipe_data: List[Dict[str, Any]]) -> List[ResourceRequirement]:
        """Convert raw recipe dicts to ResourceRequirement objects.
        
        Filters to only include resources (not equipment).
        
        Args:
            recipe_data: List of raw recipe items from API
            
        Returns:
            List of ResourceRequirement objects
        """
        requirements = []
        for item in recipe_data:
            # Only include resources (filter out equipment)
            if item.get('item_subtype') != 'resources':
                continue
            
            try:
                req = ResourceRequirement(
                    resource_id=int(item.get('item_ankama_id', 0)),
                    quantity=int(item.get('quantity', 0))
                )
                requirements.append(req)
            except (KeyError, ValueError, TypeError) as e:
                print(f"⚠️  Failed to parse recipe item: {e}")
                continue
        return requirements
    
    @staticmethod
    def _parse_image_urls(image_urls_raw: Optional[Dict[str, str]]) -> Optional[ImageURLs]:
        """Parse image URLs dict.
        
        Args:
            image_urls_raw: Raw image URLs dict from API
            
        Returns:
            ImageURLs TypedDict or None if invalid
        """
        if not image_urls_raw:
            return None
        
        try:
            return ImageURLs(
                icon=str(image_urls_raw.get('icon', '')),
                sd=str(image_urls_raw.get('sd', ''))
            )
        except (KeyError, ValueError, TypeError):
            return None
    
    def from_raw_api(self, raw: Dict[str, Any]) -> Equipment:
        """Convert raw API equipment dict to Equipment dataclass.
        
        Includes caching of effects and weights to avoid recomputation.
        
        Args:
            raw: Raw equipment dict from API
            
        Returns:
            Equipment dataclass instance
            
        Raises:
            ValueError: If required fields are missing
        """
        ankama_id = int(raw.get('ankama_id', 0))
        if ankama_id <= 0:
            raise ValueError(f"Invalid equipment ID: {ankama_id}")
        
        # Parse basic fields
        equipment = Equipment(
            ankama_id=ankama_id,
            type=ItemType(raw.get('type', {})),
            name=str(raw.get('name', 'Unknown')),
            level=int(raw.get('level', 0)),
            image_urls=self._parse_image_urls(raw.get('image_urls')),
            effects=self._parse_effects(raw.get('effects', [])),
            recipe=self._parse_recipe(raw.get('recipe', []))
        )
        
        # Compute and cache stat weight
        equipment.stat_weight = self.compute_stat_weight(equipment)
        if self.cache:
            self.cache.set_stat_weight(ankama_id, equipment.stat_weight)
        
        return equipment
    
    def from_raw_batch(self, raw_list: List[Dict[str, Any]]) -> List[Equipment]:
        """Convert multiple raw equipment dicts to Equipment list.

        Skips invalid entries with warning.
        Filters equipment by minimum stat weight (density) if configured.

        Args:
            raw_list: List of raw equipment dicts
            
        Returns:
            List of valid Equipment objects
        """
        from config import Config
        
        equipments = []
        for raw in raw_list:
            try:
                eq = self.from_raw_api(raw)
                
                # Filter by minimum density (stat_weight) if threshold is set
                if Config.MIN_EQUIPMENT_DENSITY > 0:
                    if (eq.stat_weight or 0) < Config.MIN_EQUIPMENT_DENSITY:
                        continue
                
                equipments.append(eq)
            except (ValueError, KeyError) as e:
                print(f"⚠️  Skipping invalid equipment: {e}")
                continue
        return equipments
    
    @staticmethod
    def compute_stat_weight(equipment: Equipment) -> float:
        """Compute importance weight for equipment based on its effects.
        
        Uses the stat weight table from stat_calculator module.
        
        Args:
            equipment: Equipment instance with effects
            
        Returns:
            Total weight score (higher = better)
        """
        return calculate_equipment_weight(equipment)
    
    def get_effects_cached(self, equipment_id: int) -> Optional[List[EquipmentStat]]:
        """Get equipment effects from cache or API.
        
        Args:
            equipment_id: Equipment ID to fetch
            
        Returns:
            List of EquipmentStat or None if not found
        """
        # Try cache first
        if self.cache and self.cache.has_equipment_effects(equipment_id):
            effects_raw = self.cache.get_equipment_effects(equipment_id)
            return self._parse_effects(effects_raw) if effects_raw else None
        
        # Fetch from API
        client = DofusAPIClient()
        response = client.get_equipment(equipment_id)
        if not response:
            return None
        
        effects_raw = response.get('effects', [])
        if self.cache:
            self.cache.set_equipment_effects(equipment_id, effects_raw)
        
        return self._parse_effects(effects_raw)


class ResourceLoader:
    """Transform raw resource API responses → Resource dataclasses."""
    
    def __init__(self, cache: Optional[CacheManager] = None):
        """Initialize loader.
        
        Args:
            cache: CacheManager instance for caching resources
        """
        self.cache = cache or CacheManager()
    
    @staticmethod
    def _parse_image_urls(image_urls_raw: Optional[Dict[str, str]]) -> Optional[ImageURLs]:
        """Parse image URLs dict.
        
        Args:
            image_urls_raw: Raw image URLs dict from API
            
        Returns:
            ImageURLs TypedDict or None if invalid
        """
        if not image_urls_raw:
            return None
        
        try:
            return ImageURLs(
                icon=str(image_urls_raw.get('icon', '')),
                sd=str(image_urls_raw.get('sd', ''))
            )
        except (KeyError, ValueError, TypeError):
            return None
    
    def from_raw_api(self, raw: Dict[str, Any]) -> Resource:
        """Convert raw API resource dict to Resource dataclass.
        
        Includes automatic caching.
        
        Args:
            raw: Raw resource dict from API
            
        Returns:
            Resource dataclass instance
            
        Raises:
            ValueError: If required fields are missing
        """
        ankama_id = int(raw.get('ankama_id', 0))
        if ankama_id <= 0:
            raise ValueError(f"Invalid resource ID: {ankama_id}")
        
        resource = Resource(
            ankama_id=ankama_id,
            name=str(raw.get('name', 'Unknown')),
            description=str(raw.get('description', '')),
            type=ItemType(raw.get('type', {})),
            level=int(raw.get('level', 0)),
            pods=int(raw.get('pods', 0)),
            image_urls=self._parse_image_urls(raw.get('image_urls'))
        )
        
        # Auto-cache
        if self.cache:
            self.cache.set_resource(ankama_id, raw)
        
        return resource
    
    def from_raw_batch(self, raw_list: List[Dict[str, Any]]) -> List[Resource]:
        """Convert multiple raw resource dicts to Resource list.
        
        Skips invalid entries with warning.
        
        Args:
            raw_list: List of raw resource dicts
            
        Returns:
            List of valid Resource objects
        """
        resources = []
        for raw in raw_list:
            try:
                res = self.from_raw_api(raw)
                resources.append(res)
            except (ValueError, KeyError) as e:
                print(f"⚠️  Skipping invalid resource: {e}")
                continue
        return resources
    
    def get_or_fetch(self, resource_id: int) -> Optional[Resource]:
        """Get resource from cache or fetch from API.
        
        Args:
            resource_id: Resource ID
            
        Returns:
            Resource instance or None if not found
        """
        # Try cache first
        if self.cache:
            cached = self.cache.get_resource(resource_id)
            if cached:
                try:
                    return self.from_raw_api(cached)
                except ValueError:
                    pass
        
        # Fetch from API
        client = DofusAPIClient()
        response = client.get_resource(resource_id)
        if response:
            return self.from_raw_api(response)
        
        return None
