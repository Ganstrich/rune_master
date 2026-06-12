"""Market parsing and item resolution module.

Cleans extracted price strings into integers and resolves fuzzy item names
to their official Ankama IDs by querying the local SQLite database.
"""
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, Any, Optional, List, Tuple
from data.cache_manager import CacheManager

class MarketParser:
    """Parses raw text labels and prices, mapping names to database IDs."""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self._item_name_cache: List[Tuple[int, str]] = []
        self._load_cached_item_names()

    def _load_cached_item_names(self):
        """Pre-fetch all resource and equipment names from the cache for fast matching."""
        try:
            conn = self.cache._conn
            # Fetch resources
            res_rows = conn.execute("SELECT id, name FROM resources").fetchall()
            # In config.py, equipment is loaded from raw api, but we also cache their weights
            # Let's check if we can query from cache.
            # If equipment names are not fully cached in resources, they might be in resource_cache.json or .db.
            # Let's fetch whatever we can find in the database resources table.
            for row in res_rows:
                self._item_name_cache.append((row["id"], row["name"]))
        except Exception as e:
            print(f"⚠️  Failed to pre-fetch cached item names for fuzzy matching: {e}")

    @staticmethod
    def normalize_string(s: str) -> str:
        """Strip accents, lowercase, and remove special characters for uniform comparison."""
        s = s.lower().strip()
        # Remove accents
        s = "".join(
            c for c in unicodedata.normalize("NFD", s)
            if unicodedata.category(c) != "Mn"
        )
        # Keep only alphanumeric characters and single spaces
        s = re.sub(r"[^\w\s]", "", s)
        s = re.sub(r"\s+", " ", s)
        return s.strip()

    def find_item_id(self, raw_name: str, threshold: float = 0.8) -> Optional[int]:
        """Fuzzy match raw name against cached resource names.
        
        Args:
            raw_name: The item name read by OCR.
            threshold: Minimum Jaro-Winkler/difflib ratio to accept a match.
            
        Returns:
            Ankama ID if found, otherwise None.
        """
        if not raw_name:
            return None

        norm_input = self.normalize_string(raw_name)
        if not norm_input:
            return None

        best_id = None
        best_ratio = 0.0

        for item_id, name in self._item_name_cache:
            norm_name = self.normalize_string(name)
            
            # Exact match check
            if norm_input == norm_name:
                return item_id
                
            # Fuzzy ratio check
            ratio = SequenceMatcher(None, norm_input, norm_name).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_id = item_id

        if best_ratio >= threshold:
            return best_id
            
        return None

    @staticmethod
    def clean_price(price_str: Optional[str]) -> Optional[int]:
        """Convert OCR text value into clean integer price, removing formatting and currency signs."""
        if price_str is None:
            return None

        # Remove dots, commas, spaces, currency symbols (like 'k' or 'kamas')
        cleaned = re.sub(r"[^\d]", "", price_str)
        if not cleaned:
            return None
            
        return int(cleaned)

    def parse_market_record(self, matched_layout: Dict[str, Any]) -> Dict[str, Any]:
        """Clean all fields and resolve the item ID from a layout-matched record."""
        raw_name = matched_layout.get("item_name")
        item_id = self.find_item_id(raw_name) if raw_name else None

        return {
            "item_id": item_id,
            "item_name": raw_name,
            "price_x1": self.clean_price(matched_layout.get("price_x1")),
            "price_x10": self.clean_price(matched_layout.get("price_x10")),
            "price_x100": self.clean_price(matched_layout.get("price_x100")),
            "price_x1000": self.clean_price(matched_layout.get("price_x1000"))
        }
