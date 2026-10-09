#!/usr/bin/env python3
"""Fetch a frozen snapshot of all craftable equipment, resources, and set index.

Resumable: re-running skips equipment, resources, and set mappings already
stored in the snapshot database. The second run makes ~0 network calls.
"""

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from data.api_client import DofusAPIClient


SCRIPT_VERSION = "1.0.0"
DEFAULT_DELAY = 0.15  # seconds between requests
MAX_LEVEL = 200


def fetch_game_version(client: DofusAPIClient) -> str:
    """Fetch the current game version from the API.

    Returns the version string (e.g., "3.7.7.6") or raises RuntimeError.
    """
    endpoint = f"/{client.game}/v1/meta/version"
    data = client._make_request(endpoint)
    if data is None:
        raise RuntimeError("Failed to fetch game version from API")
    version = data.get("version")
    if not version:
        raise RuntimeError("API version response missing 'version' field")
    return str(version)


def create_snapshot_dir(base_dir: Path, version_str: str) -> Path:
    """Create and return the snapshot directory."""
    snapshot_dir = base_dir / "snapshots" / version_str
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    return snapshot_dir


def init_database(db_path: Path) -> sqlite3.Connection:
    """Initialize the SQLite database with the required schema."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY,
            data BLOB NOT NULL
        );
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY,
            data BLOB NOT NULL
        );
        CREATE TABLE IF NOT EXISTS set_index (
            equipment_id INTEGER PRIMARY KEY,
            set_id INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS manifest (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.commit()
    return conn


def fetch_equipment(
    client: DofusAPIClient,
    conn: sqlite3.Connection,
    min_level: int,
    max_level: int,
) -> tuple[int, int, int]:
    """Fetch all equipment and store in database.

    Returns (count, min_level_found, max_level_found).
    Skips the API call entirely if equipment data already exists.
    """
    existing_count = conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0]
    if existing_count > 0:
        row = conn.execute(
            "SELECT MIN(json_extract(data, '$.level')), MAX(json_extract(data, '$.level')) FROM equipment"
        ).fetchone()
        return existing_count, int(row[0] or 0), int(row[1] or 0)

    equipments = client.get_all_equipments(
        item_types=Config.ITEM_TYPES,
        min_level=min_level,
        max_level=max_level,
    )

    min_found: int | None = None
    max_found = 0
    for eq in equipments:
        eq_id = int(eq.get("ankama_id", 0))
        if eq_id <= 0:
            continue
        data = json.dumps(eq, ensure_ascii=False)
        conn.execute(
            "INSERT OR REPLACE INTO equipment (id, data) VALUES (?, ?)",
            (eq_id, data),
        )
        level = int(eq.get("level", 0))
        if min_found is None or level < min_found:
            min_found = level
        max_found = max(max_found, level)

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0]
    return total, min_found if min_found is not None else 0, max_found


def fetch_set_index(client: DofusAPIClient, conn: sqlite3.Connection) -> int:
    """Fetch set index and store in database. Returns count."""
    existing = conn.execute("SELECT equipment_id, set_id FROM set_index").fetchall()
    if existing:
        return len(existing)

    set_index = client.get_equipment_set_index()

    conn.execute("DELETE FROM set_index")
    conn.executemany(
        "INSERT OR REPLACE INTO set_index (equipment_id, set_id) VALUES (?, ?)",
        [(int(k), int(v)) for k, v in set_index.items()],
    )
    conn.commit()
    return len(set_index)


def extract_resource_ids(conn: sqlite3.Connection) -> set[int]:
    """Extract all resource IDs from equipment recipes."""
    resource_ids: set[int] = set()
    for row in conn.execute("SELECT data FROM equipment"):
        data = json.loads(row[0])
        for item in data.get("recipe", []):
            if item.get("item_subtype") == "resources":
                resource_ids.add(int(item.get("item_ankama_id", 0)))
    return resource_ids


def fetch_resources(
    client: DofusAPIClient,
    conn: sqlite3.Connection,
    resource_ids: set[int],
    delay: float,
) -> tuple[int, list[int]]:
    """Fetch resources and store in database.

    Returns (count, missing_ids). Skips resources already in the database.
    """
    existing_ids = {row[0] for row in conn.execute("SELECT id FROM resources")}

    missing: list[int] = []
    sorted_ids = sorted(resource_ids)
    for i, res_id in enumerate(sorted_ids):
        if res_id in existing_ids:
            continue

        if (i + 1) % 100 == 0:
            print(f"  Fetched {i + 1}/{len(sorted_ids)} resources...")

        data = client.get_resource(res_id)
        if data is None:
            missing.append(res_id)
        else:
            conn.execute(
                "INSERT OR REPLACE INTO resources (id, data) VALUES (?, ?)",
                (res_id, json.dumps(data, ensure_ascii=False)),
            )

        time.sleep(delay)

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    return total, missing


def compute_dataset_hash(conn: sqlite3.Connection) -> str:
    """Compute a SHA-256 hash of all equipment and resource IDs."""
    h = hashlib.sha256()
    for row in conn.execute("SELECT id FROM equipment ORDER BY id"):
        h.update(str(row[0]).encode())
    for row in conn.execute("SELECT id FROM resources ORDER BY id"):
        h.update(str(row[0]).encode())
    return h.hexdigest()


def write_manifest(
    snapshot_dir: Path,
    conn: sqlite3.Connection,
    client: DofusAPIClient,
    game_version: str,
    equipment_count: int,
    resource_count: int,
    set_count: int,
    level_min: int,
    level_max: int,
    missing_resources: list[int],
) -> None:
    """Write manifest.json to the snapshot directory."""
    dataset_hash = compute_dataset_hash(conn)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "api_base_url": client.BASE_URL,
        "game_version": game_version,
        "script_version": SCRIPT_VERSION,
        "equipment_count": equipment_count,
        "resource_count": resource_count,
        "set_count": set_count,
        "level_min": level_min,
        "level_max": level_max,
        "item_types": Config.ITEM_TYPES,
        "dataset_hash": dataset_hash,
        "missing_resources": missing_resources,
    }

    manifest_path = snapshot_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    conn.execute("DELETE FROM manifest")
    for key, value in manifest.items():
        conn.execute(
            "INSERT OR REPLACE INTO manifest (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )
    conn.commit()


def print_counts_table(
    equipment_count: int,
    resource_count: int,
    set_count: int,
    level_min: int,
    level_max: int,
    missing_resources: list[int],
) -> None:
    """Print a counts table."""
    print("\n" + "=" * 60)
    print("SNAPSHOT COUNTS")
    print("=" * 60)
    print(f"  Equipment:           {equipment_count:>8}")
    print(f"  Resources:           {resource_count:>8}")
    print(f"  Set mappings:        {set_count:>8}")
    print(f"  Level range:         {level_min:>4} - {level_max}")
    print(f"  Missing resources:   {len(missing_resources):>8}")
    if missing_resources:
        preview = missing_resources[:10]
        suffix = "..." if len(missing_resources) > 10 else ""
        print(f"  Missing IDs:         {preview}{suffix}")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a frozen snapshot of Dofus crafting data"
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Game version override (default: fetch from API)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=f"Delay between requests in seconds (default: {DEFAULT_DELAY})",
    )
    parser.add_argument(
        "--max-level",
        type=int,
        default=MAX_LEVEL,
        help=f"Maximum equipment level (default: {MAX_LEVEL})",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Base data directory (default: data)",
    )
    args = parser.parse_args()

    # Determine game version
    if args.version:
        game_version = args.version
    else:
        temp_client = DofusAPIClient()
        try:
            game_version = fetch_game_version(temp_client)
        except RuntimeError as error:
            print(f"ERROR: {error}")
            return 1

    base_dir = Path(args.data_dir)
    snapshot_dir = create_snapshot_dir(base_dir, game_version)
    db_path = snapshot_dir / "snapshot.db"

    print(f"Snapshot directory: {snapshot_dir}")
    print(f"Database: {db_path}")

    conn = init_database(db_path)
    client = DofusAPIClient()

    # Fetch equipment
    print(f"\nFetching equipment (levels 1-{args.max_level})...")
    equipment_count, level_min, level_max = fetch_equipment(
        client, conn, 1, args.max_level
    )
    print(f"  Total equipment: {equipment_count}")
    print(f"  Level range: {level_min} - {level_max}")

    if equipment_count > 10000:
        print(
            f"\n  WARNING: Equipment count ({equipment_count}) exceeds 10,000."
            " This may indicate an issue."
        )
        response = input("Continue? [y/N] ")
        if response.lower() != "y":
            print("Aborted.")
            return 1

    # Fetch set index
    print("\nFetching set index...")
    set_count = fetch_set_index(client, conn)
    print(f"  Set mappings: {set_count}")

    # Extract resource IDs
    print("\nExtracting resource IDs from recipes...")
    resource_ids = extract_resource_ids(conn)
    print(f"  Unique resource IDs: {len(resource_ids)}")

    if len(resource_ids) > 5000:
        print(
            f"\n  WARNING: Resource count ({len(resource_ids)}) exceeds 5,000."
            " This may indicate an issue."
        )
        response = input("Continue? [y/N] ")
        if response.lower() != "y":
            print("Aborted.")
            return 1

    # Fetch resources
    print(f"\nFetching resources (delay: {args.delay}s)...")
    resource_count, missing_resources = fetch_resources(
        client, conn, resource_ids, args.delay
    )
    print(f"  Total resources: {resource_count}")
    print(f"  Missing: {len(missing_resources)}")

    # Write manifest
    print("\nWriting manifest...")
    write_manifest(
        snapshot_dir,
        conn,
        client,
        game_version,
        equipment_count,
        resource_count,
        set_count,
        level_min,
        level_max,
        missing_resources,
    )

    # Print counts table
    print_counts_table(
        equipment_count,
        resource_count,
        set_count,
        level_min,
        level_max,
        missing_resources,
    )

    # Fail loudly on missing resources
    if missing_resources:
        print(
            f"\n  ERROR: {len(missing_resources)} resources could not be fetched!"
        )
        print(f"   Missing IDs: {missing_resources}")
        return 1

    print("\n  Snapshot complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
