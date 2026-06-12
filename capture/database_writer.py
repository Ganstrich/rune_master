"""Database operations module for storing market prices.

Manages creation of the market_prices table and UPSERT operations for parsed items
in the existing SQLite cache database.
"""
from typing import Dict, Any, Optional
from data.cache_manager import CacheManager

class DatabaseWriter:
    """Manages SQLite storage for captured Dofus market prices."""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self._create_market_table()

    def _create_market_table(self):
        """Create the market_prices table if it does not exist."""
        try:
            conn = self.cache._conn
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_prices (
                    item_id INTEGER PRIMARY KEY,
                    price_x1 INTEGER,
                    price_x10 INTEGER,
                    price_x100 INTEGER,
                    price_x1000 INTEGER,
                    updated_at TEXT DEFAULT (datetime('now'))
                );
            """)
            conn.commit()
        except Exception as e:
            print(f"❌ Failed to create market_prices table: {e}")
            raise

    def write_prices(self, parsed_record: Dict[str, Any]) -> bool:
        """Upsert market prices for a resolved item into the SQLite database.
        
        Args:
            parsed_record: Dict containing:
                - 'item_id': Resolved Ankama ID (int)
                - 'price_x1': Optional[int]
                - 'price_x10': Optional[int]
                - 'price_x100': Optional[int]
                - 'price_x1000': Optional[int]
                
        Returns:
            True if successful, False if resolution/writing failed.
        """
        item_id = parsed_record.get("item_id")
        if item_id is None:
            name = parsed_record.get("item_name", "Unknown")
            print(f"⚠️  Skipping database write: Item '{name}' could not be resolved to an Ankama ID.")
            return False

        try:
            conn = self.cache._conn
            
            # Use UPSERT (INSERT ... ON CONFLICT) to update fields if item already exists
            conn.execute("""
                INSERT INTO market_prices (
                    item_id, price_x1, price_x10, price_x100, price_x1000, updated_at
                ) VALUES (
                    :item_id, :price_x1, :price_x10, :price_x100, :price_x1000, datetime('now')
                )
                ON CONFLICT(item_id) DO UPDATE SET
                    price_x1 = excluded.price_x1,
                    price_x10 = excluded.price_x10,
                    price_x100 = excluded.price_x100,
                    price_x1000 = excluded.price_x1000,
                    updated_at = datetime('now');
            """, parsed_record)
            
            conn.commit()
            print(f"💾 Saved prices for ID {item_id} ({parsed_record.get('item_name')}) to DB: "
                  f"x1={parsed_record.get('price_x1')}, "
                  f"x10={parsed_record.get('price_x10')}, "
                  f"x100={parsed_record.get('price_x100')}, "
                  f"x1000={parsed_record.get('price_x1000')}")
            return True
        except Exception as e:
            print(f"❌ Failed to upsert market prices for item {item_id}: {e}")
            return False

    def get_prices(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve stored market prices for a specific item.
        
        Returns:
            Dict containing prices or None if not found.
        """
        try:
            conn = self.cache._conn
            row = conn.execute(
                "SELECT price_x1, price_x10, price_x100, price_x1000, updated_at FROM market_prices WHERE item_id = ?",
                (item_id,)
            ).fetchone()
            
            if row is None:
                return None
                
            return {
                "price_x1": row["price_x1"],
                "price_x10": row["price_x10"],
                "price_x100": row["price_x100"],
                "price_x1000": row["price_x1000"],
                "updated_at": row["updated_at"]
            }
        except Exception as e:
            print(f"❌ Failed to query market prices: {e}")
            return None
