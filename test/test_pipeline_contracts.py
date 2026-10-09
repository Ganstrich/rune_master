"""Offline contract tests for the grouping pipeline."""

from pathlib import Path
import json

import pytest
import requests

from data.cache_manager import CacheManager
from data.api_client import DofusAPIClient
from main import parse_args
from models import Equipment, ResourceRequirement
from processing import ProcessingConfig, RuneMaster
from processing.equipment_filter import EquipmentFilteringStrategy
from processing.random_group_builder import RandomGroupBuilder
from visualization import HTMLGenerator


def make_equipments() -> list[Equipment]:
    """Create a small connected equipment graph without API access."""
    return [
        Equipment(
            ankama_id=index,
            type={"id": 1, "name": "sword"},
            level=20 + index,
            name=f"Offline Equipment {index}",
            stat_weight=10 + index,
            recipe=[
                ResourceRequirement(resource_id=100, quantity=2),
                ResourceRequirement(resource_id=200 + index, quantity=1),
            ],
        )
        for index in range(1, 5)
    ]


def test_random_seed_is_reproducible_without_duplicate_seeds() -> None:
    """A fixed builder seed should produce the same seed sequence."""
    equipments = make_equipments()
    builder = RandomGroupBuilder(equipments, seed=7)

    first = builder.build_multiple_random_groups(
        equipments, count=4, min_shared_resources=1
    )
    second = RandomGroupBuilder(equipments, seed=7).build_multiple_random_groups(
        equipments, count=4, min_shared_resources=1
    )

    first_seeds = [group["seed_equipment_id"] for group in first]
    second_seeds = [group["seed_equipment_id"] for group in second]
    assert first_seeds == second_seeds
    assert len(first_seeds) == len(set(first_seeds))


def test_density_filter_falls_back_when_pool_is_too_small() -> None:
    """An over-strict filter should use the configured fallback pool."""
    equipments = make_equipments()

    active_pool, was_filtered = EquipmentFilteringStrategy.get_active_pool(
        equipments,
        density_ratio=10.0,
        fallback_to_unfiltered=True,
        min_pool_size=2,
    )

    assert active_pool == equipments
    assert was_filtered is False


def test_deterministic_pipeline_returns_canonical_groups() -> None:
    """The offline graph path should produce complete group metadata."""
    config = ProcessingConfig(
        algorithm="none",
        graph_min_shared_ratio=0.0,
        graph_min_shared_count=1,
        group_min_shared_resources=1,
        group_efficiency_threshold=0.0,
    )
    groups = RuneMaster(make_equipments(), config=config).run_deterministic()

    assert groups
    assert all(group["selection_method"] == "deterministic" for group in groups)
    assert all(group["equipments"] for group in groups)
    assert all("total_ingredients" in group for group in groups)


class StubExpert:
    """Minimal expert double for testing hybrid dispatch decisions."""

    def __init__(self, groups: list[dict]) -> None:
        self.groups = groups

    def discover_groups(self, *args: object, **kwargs: object) -> list[dict]:
        return self.groups


def test_hybrid_pipeline_supplements_small_deterministic_result() -> None:
    """Hybrid mode should call the random expert below its threshold."""
    equipments = make_equipments()
    group = RandomGroupBuilder(equipments, seed=3).build_random_group(
        equipments, min_shared_resources=1
    )
    assert group is not None

    master = RuneMaster(equipments, ProcessingConfig(random_group_count=10))
    master.experts["deterministic"] = StubExpert([])
    master.experts["random"] = StubExpert([group])

    result = master.run_hybrid_grouping()

    assert result == [group]


def test_visualization_generates_index_and_group_page(tmp_path: Path) -> None:
    """A canonical offline group should render a self-contained report."""
    group = RandomGroupBuilder(make_equipments(), seed=1).build_random_group(
        make_equipments(), min_shared_resources=1
    )
    assert group is not None

    paths = HTMLGenerator(output_dir=str(tmp_path)).generate_all([group])

    generated_names = {path.name for path in map(Path, paths)}
    assert "index.html" in generated_names
    assert any(name.startswith("group_") for name in generated_names)
    assert (tmp_path / "static").is_dir()


def test_visualization_ranks_groups_by_crafting_evidence(tmp_path: Path) -> None:
    """The report should put higher-sharing groups first with stable tie-breakers."""
    generator = HTMLGenerator(output_dir=str(tmp_path))
    lower_priority = {
        "equipments": make_equipments()[:2],
        "sharing_efficiency": 0.25,
        "shared_resources_count": 1,
        "average_density": 2.0,
    }
    higher_priority = {
        "equipments": make_equipments()[2:],
        "sharing_efficiency": 0.75,
        "shared_resources_count": 2,
        "average_density": 3.0,
    }

    generator.generate_all([lower_priority, higher_priority])

    index_html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert index_html.index("Group 1") < index_html.index("Group 2")
    assert "Rank 1 - Highest-ranked" in index_html
    assert "Sharing efficiency" in index_html
    assert "Shared resources" in index_html
    assert "Average density" in index_html
    assert "Group size" in index_html
    assert "75.0%" in index_html
    assert "3.00" in index_html
    assert "group_001.html" in index_html
    assert "Offline Equipment 3" in (tmp_path / "group_001.html").read_text(encoding="utf-8")
    assert "Offline Equipment 1" in (tmp_path / "group_002.html").read_text(encoding="utf-8")


def test_visualization_writes_reproducible_manifest(tmp_path: Path) -> None:
    """The report records supplied run identity and scope without API payloads."""
    manifest = {
        "run_id": "fixed-run",
        "generated_at": "2026-09-30T00:00:00+00:00",
        "grouping_method": "deterministic",
        "scope": {"summary": "Levels 50-100; types: ring"},
    }

    HTMLGenerator(output_dir=str(tmp_path), manifest=manifest).generate_all([])

    saved = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert saved == manifest
    index_html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "fixed-run" in index_html
    assert "Levels 50-100; types: ring" in index_html


def test_visualization_exposes_id_based_combined_recipe_data(tmp_path: Path) -> None:
    """The index includes selectable groups and resource IDs for browser totals."""
    group = {
        "equipments": make_equipments()[:2],
        "total_ingredients": {
            100: {"name": "Shared Ore", "total_quantity": 4},
            200: {"name": "Unique Ore", "total_quantity": 1},
        },
    }

    HTMLGenerator(output_dir=str(tmp_path)).generate_all([group, group])

    index_html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert index_html.count('class="group-selector"') == 2
    assert '"id": "1"' in index_html
    assert '"100": {"name": "Shared Ore"' in index_html
    assert "recipe requirement summary" in index_html.lower()


def test_scope_cli_parses_and_rejects_invalid_ranges() -> None:
    """Scope validation happens before any equipment-loading call."""
    args = parse_args(["--min-level", "80", "--max-level", "120", "--item-types", "ring,sword"])
    assert args.min_level == 80
    assert args.max_level == 120
    assert args.item_types == ["ring", "sword"]

    with pytest.raises(SystemExit):
        parse_args(["--min-level", "121", "--max-level", "120"])
    with pytest.raises(SystemExit):
        parse_args(["--item-types", "unknown"])


def test_api_query_receives_effective_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """The API request includes the configured levels and item types."""
    captured: dict[str, object] = {}
    client = DofusAPIClient()

    def request(
        endpoint: str, params: dict[str, object], quiet: bool = False
    ) -> dict[str, object]:
        captured.update(params)
        return {"items": []}

    monkeypatch.setattr(client, "_make_request", request)
    client.get_all_equipments(item_types=["ring"], min_level=80, max_level=120)

    assert captured["filter[min_level]"] == 80
    assert captured["filter[max_level]"] == 120
    assert captured["filter[type.name_id]"] == "ring"


def test_api_uses_the_all_endpoint_in_a_single_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """The /all endpoint returns every match at once, so no paging is needed."""
    endpoints: list[str] = []
    pages: list[int] = []
    client = DofusAPIClient()

    def request(
        endpoint: str, params: dict[str, object], quiet: bool = False
    ) -> dict[str, object]:
        endpoints.append(endpoint)
        pages.append(int(params.get("page[number]", 0)))
        return {"items": [{"ankama_id": 1, "recipe": [{"item_ankama_id": 10}]}]}

    monkeypatch.setattr(client, "_make_request", request)
    equipments = client.get_all_equipments(item_types=["shield"], min_level=1, max_level=50)

    assert endpoints == ["/dofus3/v1/fr/items/equipment/all"]
    assert pages == [0]  # no page[...] parameter was ever sent
    assert len(equipments) == 1


def test_api_drops_equipment_without_a_recipe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Items that cannot be crafted from resources are not equipment for us."""
    client = DofusAPIClient()

    def request(
        endpoint: str, params: dict[str, object], quiet: bool = False
    ) -> dict[str, object]:
        return {
            "items": [
                {"ankama_id": 1, "recipe": [{"item_ankama_id": 10}]},
                {"ankama_id": 2, "recipe": None},
                {"ankama_id": 3},  # key absent entirely
            ]
        }

    monkeypatch.setattr(client, "_make_request", request)

    assert [eq["ankama_id"] for eq in client.get_all_equipments()] == [1]


def test_api_tolerates_malformed_all_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed or oddly shaped /all response yields an empty list, never a crash."""
    client = DofusAPIClient()

    monkeypatch.setattr(client, "_make_request", lambda *a, **k: None)
    assert client.get_all_equipments() == []
    assert client.get_all_resources() == []
    assert client.get_all_sets() == []

    def malformed(endpoint: str, params: object = None, quiet: bool = False):
        return {"items": None, "sets": "nope"}

    monkeypatch.setattr(client, "_make_request", malformed)
    assert client.get_all_equipments() == []
    assert client.get_all_resources() == []
    assert client.get_all_sets() == []


def test_api_set_index_reads_equipment_ids_from_sets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set membership comes from each panoplie's equipment_ids in one request."""
    calls: list[str] = []
    client = DofusAPIClient()

    def request(endpoint: str, params: object = None, quiet: bool = False):
        calls.append(endpoint)
        return {
            "sets": [
                {"ankama_id": 1, "equipment_ids": [10, 11, 12]},
                {"ankama_id": 2, "equipment_ids": [13]},
                {"ankama_id": 3, "equipment_ids": None},
            ]
        }

    monkeypatch.setattr(client, "_make_request", request)

    index = client.get_equipment_set_index()

    assert calls == ["/dofus3/v1/fr/sets/all"]
    assert index == {10: 1, 11: 1, 12: 1, 13: 2}


def test_api_retries_transient_failure_and_classifies_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient transport error retries, then reports a successful response."""
    calls = 0

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list[dict[str, object]]]:
            return {"items": []}

    def get(*args: object, **kwargs: object) -> Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise requests.exceptions.Timeout("temporary")
        return Response()

    monkeypatch.setattr("data.api_client.requests.get", get)
    monkeypatch.setattr("data.api_client.time.sleep", lambda _: None)
    client = DofusAPIClient()

    assert client._make_request("/test") == {"items": []}
    assert calls == 2
    assert client.last_request_status == {"endpoint": "/test", "status": "success", "attempts": 2}


def test_api_classifies_missing_and_invalid_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Permanent missing resources and malformed payloads do not retry."""
    class MissingResponse:
        status_code = 404

        def raise_for_status(self) -> None:
            raise requests.exceptions.HTTPError(response=self)

    monkeypatch.setattr("data.api_client.requests.get", lambda *args, **kwargs: MissingResponse())
    client = DofusAPIClient()
    assert client._make_request("/missing") is None
    assert client.last_request_status["status"] == "missing_resource"
    assert client.last_request_status["attempts"] == 1

    class InvalidResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[object]:
            return []

    monkeypatch.setattr("data.api_client.requests.get", lambda *args, **kwargs: InvalidResponse())
    assert client._make_request("/invalid") is None
    assert client.last_request_status["status"] == "invalid_payload"
    assert client.last_request_status["attempts"] == 1


def test_cache_reports_resource_coverage_and_freshness(tmp_path: Path) -> None:
    """Cached resources remain usable and expose explicit coverage metadata."""
    cache = CacheManager(str(tmp_path / "cache.db"))
    cache.set_resource(100, {"name": "Shared Ore"})

    status = cache.get_resource_cache_status({100, 200})
    assert status["requested"] == 2
    assert status["cached"] == 1
    assert status["oldest"] is not None
    assert cache.get_resource(100) == {"name": "Shared Ore"}
    cache.close()