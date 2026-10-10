"""API-only metrics for challenging the grouping pipeline.

Every metric here is computable from the frozen game snapshot alone: equipment
recipes, resource records and the set index. Nothing depends on prices, taux or
drop rates, because DofusAPI exposes none of them.

Definitions live in ``plans/pipeline-challenge.md`` §2 (M1-M9) and §1.1 (A1-A4).

This module is additive: nothing in the existing pipeline imports it, so adding
it cannot change grouping behaviour.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping, Sequence

DEFAULT_BAND_WIDTH = 20
HUB_BREADTH_THRESHOLD = 50
SLOT_COUNT = 17


# --------------------------------------------------------------------------
# Derived data (plan §1.1, A1-A4)
# --------------------------------------------------------------------------

def band_of(level: Any, width: int = DEFAULT_BAND_WIDTH) -> int:
    """Return the level band index for an equipment level."""
    return int(level or 0) // width


def resource_breadth(
    equipments: Iterable[Any], excluded: frozenset[int] | set[int] = frozenset()
) -> dict[int, int]:
    """A4: how many items in the pool consume each resource.

    This is *recipe ubiquity*, not game rarity. It is the only cross-item
    resource signal the API provides, and is used purely as an anti-hub signal.
    """
    breadth: Counter[int] = Counter()
    for equipment in equipments:
        for request in equipment.recipe or []:
            resource_id = int(request.resource_id)
            if resource_id in excluded:
                continue
            breadth[resource_id] += 1
    return dict(breadth)


def resource_pods(raw_resources: Mapping[int, Mapping[str, Any]]) -> dict[int, int]:
    """A1: pods per resource, read from the stored resource records."""
    pods: dict[int, int] = {}
    for resource_id, record in raw_resources.items():
        try:
            pods[int(resource_id)] = max(int(record.get("pods", 0) or 0), 0)
        except (TypeError, ValueError):
            pods[int(resource_id)] = 0
    return pods


def slot_of(equipment: Any) -> str:
    """Return the slot name for an equipment item."""
    item_type = getattr(equipment, "type", None)
    if isinstance(item_type, dict):
        return str(item_type.get("name", "unknown"))
    return "unknown"


# --------------------------------------------------------------------------
# Per-group primitives
# --------------------------------------------------------------------------

def _item_resources(equipment: Any, excluded: frozenset[int] | set[int]) -> set[int]:
    return {int(request.resource_id) for request in (equipment.recipe or [])} - set(excluded)


def group_union(members: Sequence[Any], excluded: frozenset[int] | set[int] = frozenset()) -> set[int]:
    """Distinct resources across every member of a group."""
    union: set[int] = set()
    for equipment in members:
        union |= _item_resources(equipment, excluded)
    return union


def shared_resources(
    members: Sequence[Any], excluded: frozenset[int] | set[int] = frozenset()
) -> set[int]:
    """Resources consumed by at least two members (canonical sharing definition)."""
    if len(members) < 2:
        return set()
    usage: Counter[int] = Counter()
    for equipment in members:
        for resource_id in _item_resources(equipment, excluded):
            usage[resource_id] += 1
    return {resource_id for resource_id, count in usage.items() if count >= 2}


def compression(members: Sequence[Any], excluded: frozenset[int] | set[int] = frozenset()) -> float:
    """1 - |union| / sum(|R_i|): the extensive sharing measure."""
    occurrence = sum(len(_item_resources(equipment, excluded)) for equipment in members)
    if not occurrence:
        return 0.0
    return 1.0 - len(group_union(members, excluded)) / occurrence


def group_pods(
    members: Sequence[Any],
    pods: Mapping[int, int],
    excluded: frozenset[int] | set[int] = frozenset(),
    respect_excluded: bool = True,
) -> int:
    """A1/M5: pod load of a group's shopping list."""
    total = 0
    for equipment in members:
        for request in equipment.recipe or []:
            resource_id = int(request.resource_id)
            if respect_excluded and resource_id in excluded:
                continue
            total += max(int(request.quantity), 0) * pods.get(resource_id, 0)
    return total


def ubiquity_inv(resource_id: int, breadth: Mapping[int, int]) -> float:
    """M3 variant 1: 1 / breadth."""
    count = breadth.get(resource_id, 0)
    return 1.0 / count if count else 0.0


def ubiquity_log(resource_id: int, breadth: Mapping[int, int]) -> float:
    """M3 variant 2: 1 / log(1 + breadth)."""
    import math

    count = breadth.get(resource_id, 0)
    return 1.0 / math.log(1 + count) if count else 0.0


# --------------------------------------------------------------------------
# Statistics helpers
# --------------------------------------------------------------------------

def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return float(ordered[len(ordered) // 2])


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * fraction))
    return float(ordered[index])


def _mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def _coefficient_of_variation(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    if mean == 0:
        return 0.0
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return (variance ** 0.5) / mean


# --------------------------------------------------------------------------
# Portfolio evaluation (M1-M9)
# --------------------------------------------------------------------------

def evaluate_portfolio(
    groups: Sequence[Mapping[str, Any]],
    pool: Sequence[Any],
    *,
    breadth: Mapping[int, int],
    pods: Mapping[int, int] | None = None,
    raw_recipes: Mapping[int, Sequence[Mapping[str, Any]]] | None = None,
    excluded: frozenset[int] | set[int] = frozenset(),
    band_width: int = DEFAULT_BAND_WIDTH,
) -> dict[str, Any]:
    """Score a portfolio with the API-only challenge metrics.

    ``groups`` are the group dicts produced by the pipeline (each carrying an
    ``equipments`` list). ``pool`` is the full candidate pool the run was given.
    """
    excluded = set(excluded)
    pods = pods or {}

    memberships: list[Sequence[Any]] = []
    for group in groups:
        members = group.get("equipments", []) if isinstance(group, Mapping) else []
        if members:
            memberships.append(members)

    covered_ids = {
        int(equipment.ankama_id) for members in memberships for equipment in members
    }

    # ---- M1 coverage, band-stratified -----------------------------------
    pool_by_band: Counter[int] = Counter(band_of(item.level, band_width) for item in pool)
    level_by_id = {int(item.ankama_id): item.level for item in pool}
    covered_by_band: Counter[int] = Counter(
        band_of(level_by_id[item_id], band_width) for item_id in covered_ids
    )
    coverage_by_band = {
        band: covered_by_band[band] / pool_by_band[band]
        for band in sorted(pool_by_band)
        if pool_by_band[band]
    }

    # ---- M2 band uniformity ---------------------------------------------
    coverage_cv = _coefficient_of_variation(list(coverage_by_band.values()))

    # ---- M3 / M4 ubiquity and hub concentration --------------------------
    inv_scores: list[float] = []
    log_scores: list[float] = []
    hub_shares: list[float] = []
    for members in memberships:
        shared = shared_resources(members, excluded)
        inv_total = sum(ubiquity_inv(r, breadth) for r in shared)
        log_total = sum(ubiquity_log(r, breadth) for r in shared)
        inv_scores.append(inv_total)
        log_scores.append(log_total)
        if inv_total > 0:
            hub = sum(
                ubiquity_inv(r, breadth)
                for r in shared
                if breadth.get(r, 0) >= HUB_BREADTH_THRESHOLD
            )
            hub_shares.append(hub / inv_total)

    # ---- M5 pod load ----------------------------------------------------
    pod_values = [group_pods(members, pods, excluded) for members in memberships]
    pod_values_incl = [
        group_pods(members, pods, excluded, respect_excluded=False)
        for members in memberships
    ]

    # ---- M6 slot and slot x band coverage -------------------------------
    covered_slots = {
        slot_of(equipment)
        for members in memberships
        for equipment in members
    }
    pool_cells = {
        (slot_of(item), band_of(item.level, band_width)) for item in pool
    }
    covered_cells = {
        (slot_of(equipment), band_of(equipment.level, band_width))
        for members in memberships
        for equipment in members
    }

    # ---- M7 group size and sharing profile ------------------------------
    sizes = [len(members) for members in memberships]
    shared_counts = [len(shared_resources(members, excluded)) for members in memberships]
    union_sizes = [len(group_union(members, excluded)) for members in memberships]
    compressions = [compression(members, excluded) for members in memberships]

    # ---- M8 recipe-subtype leakage --------------------------------------
    leakage: dict[str, Any] = {"available": raw_recipes is not None}
    if raw_recipes is not None:
        raw_total = 0
        non_resource = 0
        for members in memberships:
            for equipment in members:
                entries = raw_recipes.get(int(equipment.ankama_id), [])
                raw_total += len(entries)
                non_resource += sum(
                    1
                    for entry in entries
                    if entry.get("item_subtype") != "resources"
                )
        leakage = {
            "available": True,
            "raw_entries": raw_total,
            "non_resource_entries": non_resource,
            "ratio": (non_resource / raw_total) if raw_total else 0.0,
        }

    # ---- M9 between-group overlap ---------------------------------------
    unions = [group_union(members, excluded) for members in memberships]
    overlaps: list[float] = []
    for i in range(len(unions)):
        for j in range(i + 1, len(unions)):
            left, right = unions[i], unions[j]
            denominator = len(left | right)
            if denominator:
                overlaps.append(len(left & right) / denominator)

    return {
        "group_count": len(memberships),
        "pool_size": len(pool),
        "covered": len(covered_ids),
        "coverage": {
            "global": (len(covered_ids) / len(pool)) if pool else 0.0,
            "by_band": coverage_by_band,
            "pool_by_band": dict(sorted(pool_by_band.items())),
        },
        "coverage_cv": coverage_cv,
        "ubiquity": {
            "inv_median": _median(inv_scores),
            "inv_mean": _mean(inv_scores),
            "log_median": _median(log_scores),
            "log_mean": _mean(log_scores),
        },
        "hub_share_median": _median(hub_shares),
        "pods": {
            "median": _median(pod_values),
            "total": int(sum(pod_values)),
            "median_including_excluded": _median(pod_values_incl),
        },
        "slots": {
            "covered": len(covered_slots),
            "of": SLOT_COUNT,
            "ratio": len(covered_slots) / SLOT_COUNT,
        },
        "cells": {
            "covered": len(covered_cells & pool_cells),
            "populated": len(pool_cells),
            "ratio": (len(covered_cells & pool_cells) / len(pool_cells)) if pool_cells else 0.0,
        },
        "group_profile": {
            "size_median": _median(sizes),
            "size_p90": _percentile(sizes, 0.9),
            "size_max": max(sizes) if sizes else 0,
            "shared_resources_median": _median(shared_counts),
            "union_median": _median(union_sizes),
            "compression_median": _median(compressions),
        },
        "subtype_leakage": leakage,
        "between_group_overlap_mean": _mean(overlaps),
    }
