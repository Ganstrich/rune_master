"""Low-level API client for Dofus API.

Responsible ONLY for HTTP communication and raw response handling.
NO dataclass conversions - returns raw dicts.

Endpoints used (all verified against the live API, game 3.7.7.6):

    GET /{game}/v1/{lang}/items/equipment/all     all equipment, full payload
    GET /{game}/v1/{lang}/items/resources/all     all resources, full payload
    GET /{game}/v1/{lang}/sets/all                all panoplies, with member ids
    GET /{game}/v1/{lang}/items/{kind}/{id}       single item by ankama_id

The ``/all`` variants accept the same ``filter[...]`` parameters as the
paginated list endpoints but ignore ``page[...]``: every matching item comes
back in a single response with the complete payload (effects, recipe, pods,
weapon stats, conditions). They therefore need neither the ``fields[item]``
projection nor page-size negotiation, so neither appears here. The counts are
bounded (4095 equipment, 3521 resources, 940 sets on dofus3), so each is one
request.

The API is public: no authentication, no documented rate limit, and the
responses carry no rate-limit headers.
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
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, quiet: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request to API endpoint.

        Args:
            endpoint: API endpoint (e.g., '/dofus3/v1/fr/items/equipment/all')
            params: Query parameters
            quiet: Suppress the permanent-failure log line (used by probes)

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

    @staticmethod
    def _rows(payload: Optional[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
        """Extract the row list from an ``/all`` response, tolerating odd shapes."""
        if not payload:
            return []
        rows = payload.get(key)
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    def _scope_params(
        self,
        item_types: Optional[List[str]],
        min_level: Optional[int],
        max_level: Optional[int],
    ) -> Dict[str, Any]:
        """Build the shared filter params for an equipment ``/all`` request."""
        return {
            "filter[min_level]": min_level if min_level is not None else Config.MIN_LEVEL,
            "filter[max_level]": max_level if max_level is not None else Config.MAX_LEVEL,
            "filter[type.name_id]": ",".join(item_types or Config.ITEM_TYPES),
        }

    def get_all_equipments(
        self,
        item_types: Optional[List[str]] = None,
        min_level: Optional[int] = None,
        max_level: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all equipment with recipes in one request.

        The ``/all`` endpoint ignores pagination and returns the full payload
        (effects, recipe, pods, weapon stats, conditions) per item, so neither
        the ``fields[item]`` projection nor page-size negotiation is needed.

        Args:
            item_types: Equipment types to fetch (defaults to Config.ITEM_TYPES)
            min_level: Minimum equipment level (defaults to Config.MIN_LEVEL)
            max_level: Maximum equipment level (defaults to Config.MAX_LEVEL)

        Returns:
            List of raw equipment dicts that actually carry a recipe. Items
            without one cannot be crafted from resources and are dropped.
        """
        endpoint = f"/{self.game}/v1/{self.language}/items/equipment/all"
        params = self._scope_params(item_types, min_level, max_level)

        payload = self._make_request(endpoint, params)
        rows = self._rows(payload, "items")

        equipments = [item for item in rows if item.get("recipe")]
        print(f"✅ Fetched {len(equipments)} equipments with recipes")
        return equipments

    def get_all_resources(
        self,
        min_level: Optional[int] = None,
        max_level: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch every resource in one request.

        Args:
            min_level: Minimum resource level
            max_level: Maximum resource level

        Returns:
            List of raw resource dicts (name, description, type, level, pods).
        """
        endpoint = f"/{self.game}/v1/{self.language}/items/resources/all"
        params: Dict[str, Any] = {}
        if min_level is not None:
            params["filter[min_level]"] = min_level
        if max_level is not None:
            params["filter[max_level]"] = max_level

        payload = self._make_request(endpoint, params)
        resources = self._rows(payload, "items")
        print(f"✅ Fetched {len(resources)} resources")
        return resources

    def get_all_sets(self) -> List[Dict[str, Any]]:
        """Fetch every panoplie with its member equipment ids.

        The item endpoints carry no set field, so membership is only reachable
        from the sets side. ``/sets/all`` returns ``equipment_ids`` directly,
        which the paginated list endpoint omits unless explicitly projected.

        Returns:
            List of raw set dicts (name, level, equipment_ids, effects).
        """
        endpoint = f"/{self.game}/v1/{self.language}/sets/all"
        payload = self._make_request(endpoint)
        sets = self._rows(payload, "sets")
        print(f"✅ Fetched {len(sets)} sets")
        return sets

    def get_equipment_set_index(self) -> Dict[int, int]:
        """Fetch the equipment_id -> set_id map from every panoplie.

        Returns:
            Mapping of equipment ankama_id to its set ankama_id
        """
        index: Dict[int, int] = {}
        for item_set in self.get_all_sets():
            set_id = item_set.get("ankama_id")
            equipment_ids = item_set.get("equipment_ids") or []
            if set_id is None or not isinstance(equipment_ids, list):
                continue
            for equipment_id in equipment_ids:
                index[int(equipment_id)] = int(set_id)

        print(f"✅ Mapped {len(index)} equipments to a set")
        return index

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

        There is no bulk resource endpoint: each id needs its own request, so
        prefer the SQLite cache (or get_all_resources for a full sweep) over
        this in tight loops.

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
