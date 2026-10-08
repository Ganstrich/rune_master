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
        self.last_request_status: Dict[str, Any] = {"status": "idle", "attempts": 0}
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        quiet: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request to API endpoint.
        
        Args:
            endpoint: API endpoint (e.g., '/dofus3/v1/fr/items/equipment')
            params: Query parameters
            
        Returns:
            Raw JSON response as dict, or None if request failed
        """
        url = f"{self.BASE_URL}{endpoint}"
        self.last_request_status = {"endpoint": endpoint, "status": "started", "attempts": 0}
        for attempt in range(self.MAX_RETRIES):
            self.last_request_status["attempts"] = attempt + 1
            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    self.last_request_status["status"] = "invalid_payload"
                    print(f"❌ API returned unexpected payload for {endpoint}")
                    return None
                self.last_request_status["status"] = "success"
                return payload
            except requests.exceptions.HTTPError as error:
                response = error.response
                status_code = response.status_code if response is not None else None
                if status_code == 404:
                    self.last_request_status["status"] = "missing_resource"
                    print(f"⚠️ API resource was not found for {endpoint}")
                    return None
                if status_code is None or status_code < 500:
                    self.last_request_status["status"] = "permanent_failure"
                    if not quiet:
                        print(f"❌ Permanent API failure for {endpoint}: {error}")
                    return None
                error_kind = "transient_http_failure"
                self.last_request_status["status"] = error_kind
                if attempt == self.MAX_RETRIES - 1:
                    print(f"❌ Request failed for {endpoint}: {error}")
                    return None
                time.sleep(2**attempt)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
                self.last_request_status["status"] = "transient_transport_failure"
                if attempt == self.MAX_RETRIES - 1:
                    print(f"❌ Request failed for {endpoint}: {error}")
                    return None
                time.sleep(2**attempt)
            except ValueError as error:
                self.last_request_status["status"] = "invalid_payload"
                print(f"❌ Invalid API payload for {endpoint}: {error}")
                return None
            except requests.exceptions.RequestException as error:
                self.last_request_status["status"] = "transport_failure"
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
        }

        equipments: List[Dict[str, Any]] = []
        page_size = self._negotiate_page_size(endpoint, params)
        if page_size is None:
            print("✅ Fetched 0 equipments with recipes")
            return equipments

        page = 1
        while True:
            page_params = {**params, "page[size]": page_size, "page[number]": page}
            data = self._make_request(endpoint, page_params)
            if not data:
                break
            items = data.get("items", [])
            if not isinstance(items, list):
                print("❌ API equipment response contained an invalid items field")
                break
            equipments.extend(item for item in items if isinstance(item, dict) and "recipe" in item)
            if len(items) < page_size:
                break
            page += 1
        
        print(f"✅ Fetched {len(equipments)} equipments with recipes")
        return equipments

    def _negotiate_page_size(
        self, endpoint: str, params: Dict[str, Any]
    ) -> Optional[int]:
        """Return the largest usable page size for a scope.

        The API rejects page[size] larger than the total number of matching
        items, so narrow scopes must shrink the page before the first request.
        Returns None when the scope genuinely has no results.
        """
        page_size = self.DEFAULT_PAGE_SIZE
        while page_size >= 1:
            probe = {**params, "page[size]": page_size, "page[number]": 1}
            if self._make_request(endpoint, probe, quiet=True) is not None:
                return page_size
            if self.last_request_status.get("status") != "permanent_failure":
                return None
            if page_size == 1:
                return None
            page_size = max(1, page_size // 2)
        return None
    
    def get_equipment(self, equipment_id: int) -> Optional[Dict[str, Any]]:
        """Fetch single equipment by ID.
        
        Args:
            equipment_id: Ankama equipment ID
            
        Returns:
            Raw equipment dict or None if not found
        """
        endpoint = f"/{self.game}/v1/{self.language}/items/equipment/{equipment_id}"
        return self._make_request(endpoint)
    
    def get_equipment_set_index(self) -> Dict[int, int]:
        """Fetch the equipment_id → set_id map by walking the sets endpoint.

        The item endpoints carry no set field, so membership is only reachable
        from the sets side via ``fields[set]=equipment_ids``.

        Returns:
            Mapping of equipment ankama_id to its set ankama_id
        """
        endpoint = f"/{self.game}/v1/{self.language}/sets"
        index: Dict[int, int] = {}
        page = 1
        while True:
            params = {
                "fields[set]": "equipment_ids",
                "page[size]": self.DEFAULT_PAGE_SIZE,
                "page[number]": page,
            }
            data = self._make_request(endpoint, params)
            if not data:
                break
            item_sets = data.get("sets", [])
            if not isinstance(item_sets, list):
                print("❌ API sets response contained an invalid sets field")
                break
            for item_set in item_sets:
                if not isinstance(item_set, dict):
                    continue
                set_id = item_set.get("ankama_id")
                equipment_ids = item_set.get("equipment_ids") or []
                if set_id is None or not isinstance(equipment_ids, list):
                    continue
                for equipment_id in equipment_ids:
                    index[int(equipment_id)] = int(set_id)
            if len(item_sets) < self.DEFAULT_PAGE_SIZE:
                break
            page += 1

        print(f"✅ Mapped {len(index)} equipments to a set")
        return index
    
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
