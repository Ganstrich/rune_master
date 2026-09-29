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
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from config import Config


class CacheManager:
    """Persistent disk-based cache for API data.

    Manages a SQLite database to avoid re-fetching data from API.
    Safe for concurrent reads via WAL mode.

    Schema:
        resources (id INTEGER PRIMARY KEY, name TEXT, data BLOB, fetched_at TEXT)
        equipment_effects (equipment_id INTEGER PRIMARY KEY, effects BLOB, fetched_at TEXT)
        stat_weights (equipment_id INTEGER PRIMARY KEY, weight REAL NOT NULL, computed_at TEXT DEFAULT (datetime('now')))
        price_cache (item_id INTEGER NOT NULL, kind TEXT NOT NULL, unit_price REAL NOT NULL, observed_at REAL NOT NULL, source TEXT NOT NULL, PRIMARY KEY (item_id, kind, source))
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
        self._conn = sqlite3.connect(
            self._conn_path(), check_same_thread=False, timeout=30.0
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA busy_timeout=30000")
        self._conn.row_factory = sqlite3.Row

    def _conn_path(self) -> str:
        """Return the database file path."""
        return self.cache_file

    def _create_tables(self) -> None:
        """Create cache tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS cache_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
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
            CREATE TABLE IF NOT EXISTS price_cache (
                item_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                unit_price REAL NOT NULL,
                observed_at REAL NOT NULL,
                source TEXT NOT NULL,
                PRIMARY KEY (item_id, kind, source)
            );
            CREATE TABLE IF NOT EXISTS break_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                item_level INTEGER NOT NULL,
                focus TEXT,
                runes_received_json TEXT NOT NULL,
                observed_density REAL NOT NULL,
                observed_at TEXT NOT NULL,
                source TEXT NOT NULL
            );
        """)
        self._conn.execute(
            "INSERT OR IGNORE INTO cache_metadata (key, value) VALUES (?, ?)",
            ("schema_version", "1"),
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the SQLite connection when the cache is no longer needed."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "CacheManager":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @staticmethod
    def _decode_json(value: str, label: str) -> Any | None:
        """Decode a cache value, treating corruption as a cache miss."""
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            print(f"⚠️ Ignoring corrupt cached {label} entry")
            return None

    def save(self) -> None:
        """No-op for backward compatibility; setters commit writes immediately."""
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
        value = self._decode_json(row["data"], "resource")
        if not isinstance(value, dict):
            return None
        return value

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

    def set_price(
        self,
        item_id: int,
        kind: str,
        unit_price: float,
        source: str = "manual",
        observed_at: float | None = None,
    ) -> None:
        """Store a manual or captured price observation."""
        import time

        self._conn.execute(
            """INSERT OR REPLACE INTO price_cache
            (item_id, kind, unit_price, observed_at, source) VALUES (?, ?, ?, ?, ?)""",
            (item_id, kind, float(unit_price), observed_at or time.time(), source),
        )
        self._conn.commit()

    def record_break_observation(
        self,
        item_id: int,
        item_level: int,
        focus: str | None,
        runes_received: Dict[str, int],
        observed_density: float,
        source: str = "manual",
        observed_at: str | None = None,
    ) -> int:
        """Append one immutable break observation and return its row ID."""
        timestamp = observed_at or datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """INSERT INTO break_log
            (item_id, item_level, focus, runes_received_json, observed_density, observed_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                item_id,
                item_level,
                focus,
                json.dumps(runes_received, ensure_ascii=False, sort_keys=True),
                float(observed_density),
                timestamp,
                source,
            ),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def list_break_observations(self) -> list[Dict[str, Any]]:
        """Return append-only break observations in insertion order."""
        rows = self._conn.execute(
            """SELECT id, item_id, item_level, focus, runes_received_json,
            observed_density, observed_at, source FROM break_log ORDER BY id"""
        ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "item_id": int(row["item_id"]),
                "item_level": int(row["item_level"]),
                "focus": row["focus"],
                "runes_received": self._decode_json(row["runes_received_json"], "break log") or {},
                "observed_density": float(row["observed_density"]),
                "observed_at": row["observed_at"],
                "source": row["source"],
            }
            for row in rows
        ]

    def export_break_log(self) -> list[Dict[str, Any]]:
        """Return a portable representation for migration or analysis."""
        return self.list_break_observations()

    def get_price_status(
        self, item_id: int, kind: str, max_age_seconds: float | None = None
    ) -> dict[str, Any] | None:
        """Return a price record with explicit missing/stale status."""
        import time

        row = self._conn.execute(
            """SELECT item_id, kind, unit_price, observed_at, source
            FROM price_cache WHERE item_id = ? AND kind = ?
            ORDER BY observed_at DESC LIMIT 1""",
            (item_id, kind),
        ).fetchone()
        if row is None:
            return None
        age = max(time.time() - float(row["observed_at"]), 0.0)
        return {
            "item_id": int(row["item_id"]),
            "kind": row["kind"],
            "unit_price": float(row["unit_price"]),
            "observed_at": float(row["observed_at"]),
            "source": row["source"],
            "stale": max_age_seconds is not None and age > max_age_seconds,
        }

    def get_current_price(
        self, item_id: int, kind: str, max_age_seconds: float | None = None
    ) -> float | None:
        """Return a fresh price, or None for a miss or stale observation."""
        record = self.get_price_status(item_id, kind, max_age_seconds)
        if record is None or record["stale"]:
            return None
        return float(record["unit_price"])

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
        value = self._decode_json(row["effects"], "equipment effects")
        return value if isinstance(value, list) else None

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

    def get_resource_cache_status(self, resource_ids: set[int]) -> Dict[str, Any]:
        """Return cache coverage and freshness for a requested resource set."""
        if not resource_ids:
            return {"requested": 0, "cached": 0, "oldest": None, "newest": None}
        placeholders = ",".join("?" for _ in resource_ids)
        row = self._conn.execute(
            f"""SELECT COUNT(*) AS cached, MIN(fetched_at) AS oldest,
            MAX(fetched_at) AS newest FROM resources WHERE id IN ({placeholders})""",
            tuple(resource_ids),
        ).fetchone()
        return {
            "requested": len(resource_ids),
            "cached": int(row["cached"]),
            "oldest": row["oldest"],
            "newest": row["newest"],
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
