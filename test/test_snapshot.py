"""Offline tests for snapshot loading and creation."""

import json
import sqlite3
from pathlib import Path

import pytest

from data.snapshot import load_manifest, load_snapshot


def _create_minimal_snapshot(db_path: Path) -> None:
    """Create a minimal snapshot database for testing."""
    conn = sqlite3.connect(str(db_path))
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

    # Insert fake equipment
    fake_eq = {
        "ankama_id": 12345,
        "type": {"name": "sword", "id": 1},
        "name": "Fake Sword",
        "level": 50,
        "effects": [
            {
                "type": {"name": "Force", "id": 10},
                "int_minimum": 5,
                "int_maximum": 10,
                "ignore_int_min": False,
                "ignore_int_max": False,
                "formatted": "5-10 Force",
            }
        ],
        "recipe": [
            {
                "item_ankama_id": 100,
                "quantity": 2,
                "item_subtype": "resources",
            },
            {
                "item_ankama_id": 101,
                "quantity": 1,
                "item_subtype": "resources",
            },
        ],
        "image_urls": {"icon": "http://example.com/icon.png", "sd": "http://example.com/sd.png"},
    }
    conn.execute(
        "INSERT INTO equipment (id, data) VALUES (?, ?)",
        (12345, json.dumps(fake_eq)),
    )

    # Insert fake resource
    fake_res = {
        "ankama_id": 100,
        "name": "Fake Resource",
        "description": "A fake resource",
        "type": {"name": "resource", "id": 1},
        "level": 40,
        "pods": 10,
        "image_urls": {"icon": "http://example.com/res_icon.png", "sd": "http://example.com/res_sd.png"},
    }
    conn.execute(
        "INSERT INTO resources (id, data) VALUES (?, ?)",
        (100, json.dumps(fake_res)),
    )

    # Insert set index
    conn.execute(
        "INSERT INTO set_index (equipment_id, set_id) VALUES (?, ?)",
        (12345, 99),
    )

    conn.commit()
    conn.close()


def _create_manifest(snapshot_dir: Path) -> None:
    """Create a manifest.json for testing."""
    manifest = {
        "created_at": "2025-01-01T00:00:00+00:00",
        "api_base_url": "https://api.dofusdu.de",
        "script_version": "1.0.0",
        "equipment_count": 1,
        "resource_count": 1,
        "set_count": 1,
        "level_min": 50,
        "level_max": 50,
        "item_types": ["sword"],
        "dataset_hash": "abc123",
        "missing_resources": [],
    }
    with open(snapshot_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)


class TestLoadSnapshot:
    """Tests for loading snapshots."""

    def test_load_snapshot_returns_equipment(self, tmp_path: Path) -> None:
        """Test that load_snapshot returns Equipment objects."""
        db_path = tmp_path / "snapshot.db"
        _create_minimal_snapshot(db_path)

        equipments, resources, set_index = load_snapshot(tmp_path)

        assert len(equipments) == 1
        assert equipments[0].ankama_id == 12345
        assert equipments[0].name == "Fake Sword"
        assert equipments[0].level == 50
        assert equipments[0].set_id == 99

    def test_load_snapshot_returns_resources(self, tmp_path: Path) -> None:
        """Test that load_snapshot returns Resource objects."""
        db_path = tmp_path / "snapshot.db"
        _create_minimal_snapshot(db_path)

        equipments, resources, set_index = load_snapshot(tmp_path)

        assert len(resources) == 1
        assert resources[0].ankama_id == 100
        assert resources[0].name == "Fake Resource"
        assert resources[0].level == 40
        assert resources[0].pods == 10

    def test_load_snapshot_returns_set_index(self, tmp_path: Path) -> None:
        """Test that load_snapshot returns set index mapping."""
        db_path = tmp_path / "snapshot.db"
        _create_minimal_snapshot(db_path)

        equipments, resources, set_index = load_snapshot(tmp_path)

        assert set_index == {12345: 99}

    def test_load_snapshot_missing_directory_raises(self, tmp_path: Path) -> None:
        """Test that load_snapshot raises FileNotFoundError for missing directory."""
        with pytest.raises(FileNotFoundError):
            load_snapshot(tmp_path / "nonexistent")

    def test_load_snapshot_invalid_equipment_skipped(self, tmp_path: Path) -> None:
        """Test that invalid equipment entries are skipped."""
        db_path = tmp_path / "snapshot.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            CREATE TABLE equipment (id INTEGER PRIMARY KEY, data BLOB NOT NULL);
            CREATE TABLE resources (id INTEGER PRIMARY KEY, data BLOB NOT NULL);
            CREATE TABLE set_index (equipment_id INTEGER PRIMARY KEY, set_id INTEGER NOT NULL);
            CREATE TABLE manifest (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        conn.execute(
            "INSERT INTO equipment (id, data) VALUES (?, ?)",
            (0, json.dumps({"ankama_id": 0})),  # Invalid: ankama_id = 0
        )
        conn.commit()
        conn.close()

        equipments, resources, set_index = load_snapshot(tmp_path)
        assert len(equipments) == 0

    def test_load_snapshot_invalid_resource_skipped(self, tmp_path: Path) -> None:
        """Test that invalid resource entries are skipped."""
        db_path = tmp_path / "snapshot.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            CREATE TABLE equipment (id INTEGER PRIMARY KEY, data BLOB NOT NULL);
            CREATE TABLE resources (id INTEGER PRIMARY KEY, data BLOB NOT NULL);
            CREATE TABLE set_index (equipment_id INTEGER PRIMARY KEY, set_id INTEGER NOT NULL);
            CREATE TABLE manifest (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        conn.execute(
            "INSERT INTO resources (id, data) VALUES (?, ?)",
            (0, json.dumps({"ankama_id": 0})),  # Invalid: ankama_id = 0
        )
        conn.commit()
        conn.close()

        equipments, resources, set_index = load_snapshot(tmp_path)
        assert len(resources) == 0


class TestLoadManifest:
    """Tests for loading manifests."""

    def test_load_manifest(self, tmp_path: Path) -> None:
        """Test that load_manifest returns the manifest dict."""
        _create_manifest(tmp_path)

        manifest = load_manifest(tmp_path)

        assert manifest["script_version"] == "1.0.0"
        assert manifest["equipment_count"] == 1
        assert manifest["missing_resources"] == []

    def test_load_manifest_missing_file_raises(self, tmp_path: Path) -> None:
        """Test that load_manifest raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_manifest(tmp_path / "nonexistent")
