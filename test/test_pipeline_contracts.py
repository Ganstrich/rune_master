"""Offline contract tests for the grouping pipeline."""

from pathlib import Path
import json

import pytest

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

    def request(endpoint: str, params: dict[str, object]) -> dict[str, object]:
        captured.update(params)
        return {"items": []}

    monkeypatch.setattr(client, "_make_request", request)
    client.get_all_equipments(item_types=["ring"], min_level=80, max_level=120)

    assert captured["filter[min_level]"] == 80
    assert captured["filter[max_level]"] == 120
    assert captured["filter[type.name_id]"] == "ring"