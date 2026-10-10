#!/usr/bin/env python3
"""Attribute the greedy expert's coverage gap (plans/pipeline-challenge.md C3).

The shipped GreedyGroupingExpert covered 1406/2364 items (59.48%) where the
plan's simulated sweep predicted 98.71%. This replays the expert's own growth
loop and classifies every uncovered item, so the gap is attributed rather than
guessed at.

Findings it is built to distinguish:
  - singleton discards  : the seed grew nothing, so it was dropped and never
                          marked covered -> it can never join another group
  - orphaned by covered : every neighbour was already consumed by an earlier group
  - truly isolated      : the item shares no resource with the pool

Usage:
    uv run python scripts/challenge_coverage_gap.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.snapshot import load_snapshot
from processing.blocks.recipes import recipe_resource_ids
from processing.config import ProcessingConfig
from processing.filters.equipment_filter import SetExclusionFilter
from processing.valuation.focus import break_density
from processing.valuation.objective import GroupCandidate
from processing.valuation.overlap import OverlapObjective


def resolve_snapshot(version: str | None) -> Path:
    base = ROOT / "data" / "snapshots"
    if version:
        return base / version
    available = sorted(p for p in base.iterdir() if p.is_dir())
    if not available:
        raise SystemExit("No snapshots found under data/snapshots/")
    return available[-1]


def main() -> int:
    snapshot_dir = resolve_snapshot(sys.argv[1] if len(sys.argv) > 1 else None)
    equipments, _, _ = load_snapshot(snapshot_dir)

    config = ProcessingConfig()
    excluded = set(config.excluded_resource_ids)
    objective = OverlapObjective(config.group_quality_weights)

    pool, _ = SetExclusionFilter.exclude_panoplie_items(
        equipments, config.set_exclusion_min_size
    )

    by_id = {e.ankama_id: e for e in pool}
    resources = {e.ankama_id: recipe_resource_ids(e) - excluded for e in pool}
    neighbours: dict[int, set[int]] = defaultdict(set)
    for equipment_id, resource_ids in resources.items():
        for resource_id in resource_ids:
            neighbours[resource_id].add(equipment_id)

    covered: set[int] = set()
    singleton_discards: list[int] = []
    singleton_by_band: dict[int, int] = defaultdict(int)
    grown = 0

    seeds = sorted(pool, key=break_density, reverse=True)
    for seed in seeds:
        seed_id = seed.ankama_id
        if seed_id in covered or not resources[seed_id]:
            continue

        members = [seed]
        member_ids = {seed_id}
        pooled = set(resources[seed_id])
        current = GroupCandidate(members, excluded)
        current_score = objective.score(current)

        while len(members) < config.group_max_size:
            candidate_ids = {
                neighbour
                for resource_id in pooled
                for neighbour in neighbours.get(resource_id, ())
                if neighbour not in member_ids and neighbour not in covered
            }
            if not candidate_ids:
                break
            ranked = sorted(
                candidate_ids,
                key=lambda item_id: -len(resources[item_id] & pooled),
            )[: config.greedy_candidate_limit]
            best, best_score = None, current_score
            for item_id in ranked:
                score = objective.score(current.with_item(by_id[item_id]))
                if score > best_score:
                    best, best_score = item_id, score
            if best is None:
                break
            members.append(by_id[best])
            member_ids.add(best)
            pooled |= resources[best]
            current = GroupCandidate(members, excluded)
            current_score = best_score

        if len(members) < config.group_min_size:
            singleton_discards.append(seed_id)
            singleton_by_band[(seed.level or 0) // 20] += 1
            continue

        grown += 1
        covered |= member_ids

    # Classify what remains uncovered.
    uncovered = [item for item in pool if item.ankama_id not in covered]
    truly_isolated = [
        item for item in uncovered
        if not any(
            neighbours.get(resource_id, set()) - {item.ankama_id}
            for resource_id in resources[item.ankama_id]
        )
    ]
    discarded_ids = set(singleton_discards)
    residual = [
        item for item in uncovered
        if item.ankama_id not in discarded_ids and item not in truly_isolated
    ]

    report = {
        "snapshot": snapshot_dir.name,
        "pool_size": len(pool),
        "groups_grown": grown,
        "covered": len(covered),
        "coverage": len(covered) / len(pool) if pool else 0.0,
        "singleton_discards": len(singleton_discards),
        "singleton_discards_by_band": dict(sorted(singleton_by_band.items())),
        "truly_isolated": len(truly_isolated),
        "residual_uncovered": len(residual),
        "coverage_if_singletons_kept": (
            (len(covered) + len(singleton_discards)) / len(pool) if pool else 0.0
        ),
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))
    out = ROOT / "plans" / "coverage-gap.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
