"""Tests for the API-only challenge metrics (plans/pipeline-challenge.md §2)."""

import pytest

from models import Equipment, ResourceRequirement
from analysis.challenge_metrics import (
    band_of,
    compression,
    evaluate_portfolio,
    group_pods,
    resource_breadth,
    resource_pods,
    shared_resources,
    slot_of,
    ubiquity_inv,
    ubiquity_log,
)


def make_equipment(
    ankama_id, recipe, set_id=None, level=50, type_name="test", stat_weight=100.0
):
    return Equipment(
        ankama_id=ankama_id,
        type={"id": 1, "name": type_name},
        level=level,
        name=f"Equipment {ankama_id}",
        stat_weight=stat_weight,
        recipe=[
            ResourceRequirement(resource_id=resource_id, quantity=quantity)
            for resource_id, quantity in recipe
        ],
        set_id=set_id,
    )


# --- Derived data (plan §1.1) ---

def test_band_of_partitions_by_twenty():
    assert band_of(1) == 0
    assert band_of(19) == 0
    assert band_of(20) == 1
    assert band_of(200) == 10
    assert band_of(None) == 0


def test_breadth_counts_items_consuming_each_resource():
    equipments = [
        make_equipment(1, [(10, 1), (20, 2)]),
        make_equipment(2, [(10, 3)]),
        make_equipment(3, [(30, 1)]),
    ]

    breadth = resource_breadth(equipments)

    assert breadth == {10: 2, 20: 1, 30: 1}


def test_breadth_skips_excluded_resources():
    equipments = [
        make_equipment(1, [(10, 1), (20, 2)]),
        make_equipment(2, [(10, 1), (20, 1)]),
    ]

    breadth = resource_breadth(equipments, excluded=frozenset({20}))

    assert breadth == {10: 2}


def test_pods_read_from_resource_records():
    records = {1: {"pods": 5}, 2: {"pods": None}, 3: {}}

    pods = resource_pods(records)

    assert pods == {1: 5, 2: 0, 3: 0}


# --- Per-group primitives ---

def test_shared_resources_needs_two_members():
    equipment = [make_equipment(1, [(10, 1)])]

    assert shared_resources(equipment) == set()

    pair = [make_equipment(1, [(10, 1)]), make_equipment(2, [(10, 1), (20, 1)])]
    assert shared_resources(pair) == {10}


def test_compression_of_identical_recipes():
    identical = [
        make_equipment(1, [(10, 1), (20, 1)]),
        make_equipment(2, [(10, 1), (20, 1)]),
    ]

    assert compression(identical) == pytest.approx(0.5)


def test_compression_of_disjoint_recipes_is_zero():
    disjoint = [
        make_equipment(1, [(10, 1)]),
        make_equipment(2, [(20, 1)]),
    ]

    assert compression(disjoint) == 0.0


def test_group_pods_multiplies_quantity_by_pods():
    members = [
        make_equipment(1, [(10, 3)]),
        make_equipment(2, [(10, 2), (20, 1)]),
    ]
    pods = {10: 5, 20: 10}

    assert group_pods(members, pods) == 5 * 3 + 5 * 2 + 10 * 1


def test_group_pods_can_include_excluded():
    """M5 reports both, so the effect of the exclusion stays visible."""
    members = [make_equipment(1, [(10, 3), (20, 4)])]
    pods = {10: 5, 20: 10}

    assert group_pods(members, pods, excluded={20}) == 15
    assert group_pods(members, pods, excluded={20}, respect_excluded=False) == 55


def test_ubiquity_weightings_prefer_scarce_resources():
    breadth = {1: 2, 2: 50}

    assert ubiquity_inv(1, breadth) > ubiquity_inv(2, breadth)
    assert ubiquity_log(1, breadth) > ubiquity_log(2, breadth)
    assert ubiquity_inv(1, breadth) == pytest.approx(0.5)
    assert ubiquity_inv(99, breadth) == 0.0


# --- Portfolio evaluation (M1-M9) ---

def build_pool():
    """Five items spanning five bands, with one slot repeated."""
    return [
        make_equipment(1, [(10, 1)], level=10, type_name="hat"),
        make_equipment(2, [(10, 1)], level=25, type_name="boots"),
        make_equipment(3, [(20, 1)], level=45, type_name="ring"),
        make_equipment(4, [(20, 1)], level=85, type_name="hat"),
        make_equipment(5, [(30, 1)], level=200, type_name="cloak"),
    ]


def test_portfolio_coverage_and_band_breakdown():
    pool = build_pool()
    groups = [{"equipments": [pool[0], pool[1]]}]

    report = evaluate_portfolio(groups, pool, breadth={10: 2, 20: 2, 30: 1})

    assert report["covered"] == 2
    assert report["coverage"]["global"] == pytest.approx(0.4)
    # Bands: 0={item1@10}, 1={item2@25}, 2={item3@45}, 4={item4@85}, 10={item5@200}
    # The group covers items 1 and 2.
    assert report["coverage"]["by_band"][0] == pytest.approx(1.0)
    assert report["coverage"]["by_band"][1] == pytest.approx(1.0)
    assert report["coverage"]["by_band"][2] == pytest.approx(0.0)
    assert report["coverage"]["by_band"][4] == pytest.approx(0.0)
    assert report["coverage"]["by_band"][10] == pytest.approx(0.0)


def test_portfolio_reports_slot_and_cell_coverage():
    pool = build_pool()
    groups = [{"equipments": [pool[0], pool[1]]}]

    report = evaluate_portfolio(groups, pool, breadth={10: 2})

    assert report["slots"]["covered"] == 2
    assert report["slots"]["of"] == 17
    assert report["cells"]["populated"] == 5


def test_portfolio_detects_hub_driven_sharing():
    """M4: sharing a breadth-200 resource must score as hub concentration."""
    pool = [
        make_equipment(1, [(10, 1)]),
        make_equipment(2, [(10, 1)]),
    ]
    breadth = {10: 200}

    report = evaluate_portfolio(
        [{"equipments": pool}], pool, breadth=breadth
    )

    assert report["hub_share_median"] == pytest.approx(1.0)
    assert report["ubiquity"]["inv_median"] == pytest.approx(0.005)


def test_portfolio_reports_subtype_leakage_when_recipes_available():
    pool = build_pool()
    raw = {
        1: [{"item_subtype": "resources"}],
        2: [{"item_subtype": "consumables"}],
    }
    groups = [{"equipments": [pool[0], pool[1]]}]

    report = evaluate_portfolio(
        groups, pool, breadth={10: 2}, raw_recipes=raw
    )

    leakage = report["subtype_leakage"]
    assert leakage["available"] is True
    assert leakage["raw_entries"] == 2
    assert leakage["non_resource_entries"] == 1
    assert leakage["ratio"] == pytest.approx(0.5)


def test_portfolio_marks_leakage_unavailable_without_recipes():
    pool = build_pool()
    report = evaluate_portfolio(
        [{"equipments": [pool[0]]}], pool, breadth={10: 2}
    )

    assert report["subtype_leakage"] == {"available": False}


def test_portfolio_measures_between_group_overlap():
    pool = [
        make_equipment(1, [(10, 1), (20, 1)]),
        make_equipment(2, [(10, 1), (20, 1)]),
        make_equipment(3, [(10, 1)]),
        make_equipment(4, [(10, 1)]),
    ]
    groups = [
        {"equipments": [pool[0], pool[1]]},
        {"equipments": [pool[2], pool[3]]},
    ]

    report = evaluate_portfolio(groups, pool, breadth={10: 4, 20: 2})

    # unions are {10,20} and {10}: intersection 1, union 2 -> 0.5
    assert report["between_group_overlap_mean"] == pytest.approx(0.5)


def test_empty_portfolio_is_reported_not_raised():
    report = evaluate_portfolio([], build_pool(), breadth={})

    assert report["group_count"] == 0
    assert report["coverage"]["global"] == 0.0
    assert report["group_profile"]["size_max"] == 0
