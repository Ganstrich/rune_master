"""Low-level API client for Dofus API.

Responsible ONLY for HTTP communication and raw response handling.
NO dataclass conversions - returns raw dicts.
"""
import time
from typing import Any, Dict, List, Optional

import requests

from config import Config


class DofusAPIClient:
    """Low-level HTTP client for Dofus API.
    
    Handles:
    - HTTP requests to api.dofusdu.de
    - Error handling and retries
    - Raw JSON response management
    
    Does NOT handle:
    - Caching (handled by CacheManager)
    - Converting to dataclasses (handled by Loaders)
    """
    
    BASE_URL = "https://api.dofusdu.de"
    DEFAULT_TIMEOUT = 30
    DEFAULT_PAGE_SIZE = 100
    MAX_RETRIES = 3
    
    def __init__(
        self,
        game: str = Config.GAME,
        language: str = Config.LANGUAGE,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """Initialize API client.
        
        Args:
            game: Game name (e.g., 'dofus3')
            language: Language code (e.g., 'fr')
            timeout: Request timeout in seconds
        """
        self.game = game
        self.language = language
        self.timeout = timeout
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request to API endpoint.
        
        Args:
            endpoint: API endpoint (e.g., '/dofus3/v1/fr/items/equipment')
            params: Query parameters
            
        Returns:
            Raw JSON response as dict, or None if request failed
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    print(f"❌ API returned unexpected payload for {endpoint}")
                    return None
                return payload
            except (requests.exceptions.RequestException, ValueError) as error:
                if attempt == self.MAX_RETRIES - 1:
                    print(f"❌ Request failed for {endpoint}: {error}")
                    return None
                time.sleep(2**attempt)
        return None
    
    def get_all_equipments(
        self,
        item_types: Optional[List[str]] = None,
        min_level: Optional[int] = None,
        max_level: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all equipments with recipes.
        
        Args:
            item_types: Equipment types to fetch (defaults to Config.ITEM_TYPES)
            min_level: Minimum equipment level (defaults to Config.MIN_LEVEL)
            max_level: Maximum equipment level (defaults to Config.MAX_LEVEL)
            
        Returns:
            List of raw equipment dicts from API (only those with recipes)
        """
        item_types = item_types or Config.ITEM_TYPES
        min_level = min_level if min_level is not None else Config.MIN_LEVEL
        max_level = max_level if max_level is not None else Config.MAX_LEVEL
        
        endpoint = f"/{self.game}/v1/{self.language}/items/equipment"
        
        params = {
            f'sort[{Config.SORT_BY}]': Config.SORT_ORDER,
            'filter[min_level]': min_level,
            'filter[max_level]': max_level,
            'fields[item]': ','.join(Config.FIELDS),
            'filter[type.name_id]': ','.join(item_types),
            'page[size]': self.DEFAULT_PAGE_SIZE,
        }

        equipments: List[Dict[str, Any]] = []
        page = 1
        while True:
            page_params = {**params, "page[number]": page}
            data = self._make_request(endpoint, page_params)
            if not data:
                break
            items = data.get("items", [])
            if not isinstance(items, list):
                print("❌ API equipment response contained an invalid items field")
                break
            equipments.extend(item for item in items if isinstance(item, dict) and "recipe" in item)
            if len(items) < self.DEFAULT_PAGE_SIZE:
                break
            page += 1
        
        print(f"✅ Fetched {len(equipments)} equipments with recipes")
        return equipments
    
    def get_equipment(self, equipment_id: int) -> Optional[Dict[str, Any]]:
        """Fetch single equipment by ID.
        
        Args:
            equipment_id: Ankama equipment ID
            
        Returns:
            Raw equipment dict or None if not found
        """
        endpoint = f"/{self.game}/v1/{self.language}/items/equipment/{equipment_id}"
        return self._make_request(endpoint)
    
    def get_resource(self, resource_id: int) -> Optional[Dict[str, Any]]:
        """Fetch single resource by ID.
        
        Args:
            resource_id: Ankama resource ID
            
        Returns:
            Raw resource dict or None if not found
        """
        endpoint = f"/{self.game}/v1/{self.language}/items/resources/{resource_id}"
        return self._make_request(endpoint)
    
    def get_resources_batch(self, resource_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch multiple resources by IDs (individually).
        
        WARNING: Makes multiple API calls. Consider caching!
        
        Args:
            resource_ids: List of resource IDs
            
        Returns:
            List of raw resource dicts
        """
        resources: List[Dict[str, Any]] = []
        for res_id in resource_ids:
            res_data = self.get_resource(res_id)
            if isinstance(res_data, dict):
                resources.append(res_data)
        return resources
