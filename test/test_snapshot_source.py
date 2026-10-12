"""Tests for snapshot version gating and the offline resource bridge."""

import json
from pathlib import Path

import pytest

import data.snapshot_source as ss
from data.api_client import DofusAPIClient
from data.snapshot_source import _ResourceCacheBridge
from models import Resource


class FakeAPI:
    """Stand-in that reports a fixed version and refuses other requests."""

    game = "dofus3"

    def __init__(self, version):
        self._version = version

    def _make_request(self, endpoint, params=None, quiet=False):
        if "meta/version" in endpoint:
            return {"version": self._version}
        raise AssertionError(f"unexpected request: {endpoint}")


class DeadAPI:
    game = "dofus3"

    def _make_request(self, endpoint, params=None, quiet=False):
        return None


def test_matching_version_selects_the_snapshot() -> None:
    match = ss.find_matching_snapshot(FakeAPI("3.7.7.6"))

    assert match is not None
    assert match.version == "3.7.7.6"
    assert match.database.name == "snapshot.db"


def test_mismatched_version_is_never_used(tmp_path: Path) -> None:
    """A stale snapshot must not be trusted just because it is the only one."""
    stale = tmp_path / "3.7.7.5"
    stale.mkdir()
    (stale / "snapshot.db").write_bytes(b"x")
    (stale / "manifest.json").write_text(
        json.dumps({"game_version": "3.7.7.5"}), encoding="utf-8"
    )

    assert ss.find_matching_snapshot(FakeAPI("3.7.7.6"), root=tmp_path) is None


def test_unreachable_api_falls_back(tmp_path: Path) -> None:
    (tmp_path / "3.7.7.6").mkdir()
    assert ss.find_matching_snapshot(DeadAPI(), root=tmp_path) is None


def test_snapshot_without_manifest_is_skipped(tmp_path: Path) -> None:
    """The directory name is not evidence of the version it holds."""
    unverified = tmp_path / "3.7.7.6"
    unverified.mkdir()
    (unverified / "snapshot.db").write_bytes(b"x")

    assert ss.find_matching_snapshot(FakeAPI("3.7.7.6"), root=tmp_path) is None


def test_snapshot_without_database_is_skipped(tmp_path: Path) -> None:
    empty = tmp_path / "3.7.7.6"
    empty.mkdir()
    (empty / "manifest.json").write_text(
        json.dumps({"game_version": "3.7.7.6"}), encoding="utf-8"
    )

    assert ss.find_matching_snapshot(FakeAPI("3.7.7.6"), root=tmp_path) is None


def test_corrupt_manifest_is_skipped(tmp_path: Path) -> None:
    corrupt = tmp_path / "3.7.7.6"
    corrupt.mkdir()
    (corrupt / "snapshot.db").write_bytes(b"x")
    (corrupt / "manifest.json").write_text("{not json", encoding="utf-8")

    assert ss.find_matching_snapshot(FakeAPI("3.7.7.6"), root=tmp_path) is None


def test_resource_bridge_serves_names_and_icons() -> None:
    resources = [
        Resource(
            ankama_id=274,
            name="Pièce du Puzzle",
            description="desc",
            type={"name": "Pierre brute", "id": 91},
            level=43,
            pods=5,
            image_urls={"icon": "http://x/icon.png", "sd": "http://x/sd.png"},
        )
    ]
    bridge = _ResourceCacheBridge(resources)

    payload = bridge.get_resource(274)

    assert payload is not None
    assert payload["name"] == "Pièce du Puzzle"
    assert payload["image_urls"]["icon"] == "http://x/icon.png"
    assert bridge.get_resource(999) is None


def test_resource_bridge_handles_empty_pool() -> None:
    bridge = _ResourceCacheBridge([])

    assert bridge.get_resource(1) is None
