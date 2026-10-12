"""Resolve which frozen snapshot to use, given the live API version.

The pipeline reads equipment from a frozen snapshot instead of re-fetching
every run, so the snapshot and the live API must describe the same game
version. This module answers one question: *which snapshot directory matches
the API right now?*

- the API advertises its version at ``/{game}/v1/meta/version``;
- each snapshot records the version it was built from in ``manifest.json``;
- when they match, the snapshot is a faithful stand-in and no network fetch
  of equipment/resources/sets is needed at all.

When they differ, the caller must not silently use the stale snapshot. The
mismatch is reported so the operator can re-run
``scripts/snapshot_data.py`` to refresh it.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from data.api_client import DofusAPIClient
from models import Resource

SNAPSHOT_ROOT = Path(__file__).resolve().parent.parent / "data" / "snapshots"


@dataclass(frozen=True)
class SnapshotMatch:
    """Result of matching the live API version against local snapshots."""

    path: Path
    version: str

    @property
    def database(self) -> Path:
        return self.path / "snapshot.db"


def read_snapshot_version(snapshot_dir: Path) -> Optional[str]:
    """Return the game version a snapshot was built from, or None."""
    manifest_path = Path(snapshot_dir) / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    version = manifest.get("game_version")
    return str(version) if version else None


def list_snapshots(root: Path = SNAPSHOT_ROOT) -> List[tuple[str, Path]]:
    """List local snapshots as (version, path) pairs.

    Only directories carrying a ``manifest.json`` with a ``game_version`` are
    offered. Falling back to the directory name would let a directory named
    after a version be trusted with no evidence that it actually holds that
    version's data.
    """
    root = Path(root)
    if not root.is_dir():
        return []
    found: List[tuple[str, Path]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not (entry / "snapshot.db").exists():
            continue
        version = read_snapshot_version(entry)
        if version is not None:
            found.append((version, entry))
    return found


def find_matching_snapshot(
    api: Any, root: Path = SNAPSHOT_ROOT
) -> Optional[SnapshotMatch]:
    """Return the snapshot matching the live API version, or None.

    A single lightweight ``/meta/version`` call is the only network access;
    it is much cheaper than downloading the whole equipment set.
    """
    payload = api._make_request(f"/{api.game}/v1/meta/version")
    if not payload:
        return None
    live_version = payload.get("version")
    if not live_version:
        return None
    live_version = str(live_version)

    for version, path in list_snapshots(root):
        if version == live_version:
            return SnapshotMatch(path=path, version=live_version)
    return None


class _ResourceCacheBridge:
    """Serve resource payloads from an in-memory snapshot resource list.

    `GroupMetrics.aggregate_resources` calls ``cache_manager.get_resource(id)``
    to fill in resource names and icons. This honours exactly that call so
    the rest of the pipeline needs no change for the snapshot path.
    """

    def __init__(self, resources: Iterable[Resource]):
        self._resources: Dict[int, dict] = {
            int(res.ankama_id): {
                "ankama_id": res.ankama_id,
                "name": res.name,
                "description": res.description,
                "type": res.type,
                "level": res.level,
                "pods": res.pods,
                "image_urls": res.image_urls,
            }
            for res in resources
        }

    def get_resource(self, resource_id: int) -> Optional[Dict[str, Any]]:
        """Return the raw resource payload, or None when unknown."""
        return self._resources.get(int(resource_id))


class _NoOpAPI:
    """Stand-in for `DofusAPIClient` when no live request is made.

    The snapshot path is fully offline, so it exposes only the attribute the
    pipeline reads: ``resource_cache_status``.
    """

    def __init__(self) -> None:
        self.resource_cache_status: Dict[str, Any] = {
            "status": "snapshot",
            "covered": 0,
            "requested": 0,
            "failed_ids": [],
        }
