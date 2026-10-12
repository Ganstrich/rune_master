"""Load equipment, resources, and set index from a frozen snapshot.

This module provides a drop-in replacement for the live API loaders,
returning the same model objects so downstream code cannot tell the
difference between live and snapshot data.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from data.loaders import EquipmentLoader, ResourceLoader
from models import Equipment, ItemType, Resource


def load_snapshot(path: str | Path) -> tuple[list[Equipment], list[Resource], dict[int, int]]:
    """Load equipment, resources, and set index from a snapshot directory.

    Args:
        path: Path to the snapshot directory (containing snapshot.db).

    Returns:
        Tuple of (equipments, resources, set_index) where:
        - equipments: List of Equipment dataclass instances
        - resources: List of Resource dataclass instances
        - set_index: Dict mapping equipment_id -> set_id

    Raises:
        FileNotFoundError: If snapshot.db does not exist.
        ValueError: If the snapshot is corrupted or incomplete.
    """
    snapshot_dir = Path(path)
    db_path = snapshot_dir / "snapshot.db"

    if not db_path.exists():
        raise FileNotFoundError(f"Snapshot database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        # Load set index
        set_index: dict[int, int] = {}
        for row in conn.execute("SELECT equipment_id, set_id FROM set_index"):
            set_index[int(row["equipment_id"])] = int(row["set_id"])

        # Load equipment
        equipments: list[Equipment] = []
        for row in conn.execute("SELECT data FROM equipment ORDER BY id"):
            raw = json.loads(row["data"])
            eq = _load_equipment(raw, set_index)
            if eq is not None:
                equipments.append(eq)

        # Load resources
        resources: list[Resource] = []
        for row in conn.execute("SELECT data FROM resources ORDER BY id"):
            raw = json.loads(row["data"])
            res = _load_resource(raw)
            if res is not None:
                resources.append(res)

        return equipments, resources, set_index

    finally:
        conn.close()


def _load_equipment(raw: dict[str, Any], set_index: dict[int, int]) -> Equipment | None:
    """Convert a raw equipment dict to an Equipment dataclass.

    Uses the same parsing logic as EquipmentLoader.from_raw_api.
    """
    ankama_id = int(raw.get("ankama_id", 0))
    if ankama_id <= 0:
        return None

    # Parse effects
    effects = EquipmentLoader._parse_effects(raw.get("effects", []))

    # Parse recipe
    recipe_items = EquipmentLoader._parse_recipe(raw.get("recipe", []))

    # Parse image URLs
    image_urls = EquipmentLoader._parse_image_urls(raw.get("image_urls"))

    # Get set ID from index
    set_id = set_index.get(ankama_id)

    # Create equipment
    equipment = Equipment(
        ankama_id=ankama_id,
        type=ItemType(raw.get("type", {})),
        name=str(raw.get("name", "Unknown")),
        level=int(raw.get("level", 0)),
        image_urls=image_urls,
        effects=effects,
        recipe=recipe_items,
        set_id=set_id,
    )

    # Compute stat weight
    equipment.stat_weight = EquipmentLoader.compute_stat_weight(equipment)

    return equipment


def _load_resource(raw: dict[str, Any]) -> Resource | None:
    """Convert a raw resource dict to a Resource dataclass.

    Uses the same parsing logic as ResourceLoader.from_raw_api.
    """
    ankama_id = int(raw.get("ankama_id", 0))
    if ankama_id <= 0:
        return None

    image_urls = ResourceLoader._parse_image_urls(raw.get("image_urls"))

    return Resource(
        ankama_id=ankama_id,
        name=str(raw.get("name", "Unknown")),
        description=str(raw.get("description", "")),
        type=ItemType(raw.get("type", {})),
        level=int(raw.get("level", 0)),
        pods=int(raw.get("pods", 0)),
        image_urls=image_urls,
    )


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Load and return the manifest.json from a snapshot directory.

    Args:
        path: Path to the snapshot directory.

    Returns:
        Dict containing manifest metadata.

    Raises:
        FileNotFoundError: If manifest.json does not exist.
    """
    manifest_path = Path(path) / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)
