"""Persistent disk cache for expensive API operations.

Caches:
- Resource information (to avoid re-fetching from API)
- Equipment effects (to avoid re-computing)
- Stat weights (to avoid re-calculating)

SQLite-backed storage with WAL mode for safe concurrent reads.
"""

import json
import os
import sqlite3
from typing import Any, Dict, Optional

from config import Config


class CacheManager:
    """Persistent disk-based cache for API data.

    Manages a SQLite database to avoid re-fetching data from API.
    Safe for concurrent reads via WAL mode.

    Schema:
        resources (id INTEGER PRIMARY KEY, name TEXT, data BLOB, fetched_at TEXT)
        equipment_effects (equipment_id INTEGER PRIMARY KEY, effects BLOB, fetched_at TEXT)
        stat_weights (equipment_id INTEGER PRIMARY KEY, weight REAL, computed_at TEXT)
    """

    def __init__(self, cache_file: str = Config.CACHE_FILE):
        """Initialize cache manager.

        Args:
            cache_file: Path to SQLite database file
        """
        self.cache_file = cache_file
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._create_tables()

    def _connect(self) -> None:
        """Open SQLite connection with WAL mode for concurrent read safety."""
        db_dir = os.path.dirname(self.cache_file)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._conn = sqlite3.connect(self._conn_path(), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.row_factory = sqlite3.Row

    def _conn_path(self) -> str:
        """Return the database file path."""
        return self.cache_file

    def _create_tables(self) -> None:
        """Create cache tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                data BLOB NOT NULL,
                fetched_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS equipment_effects (
                equipment_id INTEGER PRIMARY KEY,
                effects BLOB NOT NULL,
                fetched_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS stat_weights (
                equipment_id INTEGER PRIMARY KEY,
                weight REAL NOT NULL,
                computed_at TEXT DEFAULT (datetime('now'))
            );
        """)
        self._conn.commit()

    def save(self) -> None:
        """No-op for backward compatibility. SQLite auto-commits each statement."""
        pass

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
        row = self._conn.execute(
            "SELECT data FROM resources WHERE id = ?", (resource_id,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["data"])

    def set_resource(self, resource_id: int, data: Dict[str, Any]) -> None:
        """Cache resource data.

        Args:
            resource_id: Resource ID
            data: Raw resource data from API
        """
        name = data.get("name", "")
        blob = json.dumps(data, ensure_ascii=False)
        self._conn.execute(
            "INSERT OR REPLACE INTO resources (id, name, data) VALUES (?, ?, ?)",
            (resource_id, name, blob),
        )
        self._conn.commit()

    def has_resource(self, resource_id: int) -> bool:
        """Check if resource is cached.

        Args:
            resource_id: Resource ID

        Returns:
            True if resource is in cache
        """
        row = self._conn.execute(
            "SELECT 1 FROM resources WHERE id = ?", (resource_id,)
        ).fetchone()
        return row is not None

    def get_resource_name(self, resource_id: int) -> Optional[str]:
        """Get cached resource name.

        Args:
            resource_id: Resource ID

        Returns:
            Resource name or None if not cached
        """
        row = self._conn.execute(
            "SELECT name FROM resources WHERE id = ?", (resource_id,)
        ).fetchone()
        if row is not None:
            return row["name"]
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
        row = self._conn.execute(
            "SELECT effects FROM equipment_effects WHERE equipment_id = ?",
            (equipment_id,),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["effects"])

    def set_equipment_effects(self, equipment_id: int, effects: list) -> None:
        """Cache equipment effects.

        Args:
            equipment_id: Equipment ID
            effects: List of effect data from API
        """
        blob = json.dumps(effects, ensure_ascii=False)
        self._conn.execute(
            "INSERT OR REPLACE INTO equipment_effects (equipment_id, effects) VALUES (?, ?)",
            (equipment_id, blob),
        )
        self._conn.commit()

    def has_equipment_effects(self, equipment_id: int) -> bool:
        """Check if equipment effects are cached.

        Args:
            equipment_id: Equipment ID

        Returns:
            True if effects are in cache
        """
        row = self._conn.execute(
            "SELECT 1 FROM equipment_effects WHERE equipment_id = ?",
            (equipment_id,),
        ).fetchone()
        return row is not None

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
        row = self._conn.execute(
            "SELECT weight FROM stat_weights WHERE equipment_id = ?",
            (equipment_id,),
        ).fetchone()
        if row is None:
            return None
        return float(row["weight"])

    def set_stat_weight(self, equipment_id: int, weight: float) -> None:
        """Cache computed stat weight.

        Args:
            equipment_id: Equipment ID
            weight: Computed weight value
        """
        self._conn.execute(
            "INSERT OR REPLACE INTO stat_weights (equipment_id, weight) VALUES (?, ?)",
            (equipment_id, float(weight)),
        )
        self._conn.commit()

    def has_stat_weight(self, equipment_id: int) -> bool:
        """Check if stat weight is cached.

        Args:
            equipment_id: Equipment ID

        Returns:
            True if weight is in cache
        """
        row = self._conn.execute(
            "SELECT 1 FROM stat_weights WHERE equipment_id = ?",
            (equipment_id,),
        ).fetchone()
        return row is not None

    # ========================================================================
    # CACHE STATS - Monitoring and debugging
    # ========================================================================

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dict with counts of cached items
        """
        resources = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM resources"
        ).fetchone()["cnt"]
        effects = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM equipment_effects"
        ).fetchone()["cnt"]
        weights = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM stat_weights"
        ).fetchone()["cnt"]
        return {
            "cached_resources": resources,
            "cached_effects": effects,
            "cached_weights": weights,
        }

    def clear(self) -> None:
        """Clear all cache (for testing purposes)."""
        self._conn.execute("DELETE FROM resources")
        self._conn.execute("DELETE FROM equipment_effects")
        self._conn.execute("DELETE FROM stat_weights")
        self._conn.commit()

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"CacheManager("
            f"file={self.cache_file}, "
            f"resources={stats['cached_resources']}, "
            f"effects={stats['cached_effects']}, "
            f"weights={stats['cached_weights']})"
        )
