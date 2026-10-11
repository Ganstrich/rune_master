#!/usr/bin/env python3
"""Attribute the greedy expert's coverage gap, using the SHIPPED expert.

The previous version of this script re-implemented the greedy growth loop and
omitted the ``GroupAcceptancePolicy`` gate. That made its output internally
impossible (``coverage_if_singletons_kept`` exceeded 1.0) and mis-attributed the
gap to "singleton discards". This version runs ``RuneMaster.run_greedy()`` and
classifies whatever the real pipeline left uncovered, then replays the same
growth loop *with the policy applied* to attribute the loss.

Findings it distinguishes:
  - empty recipe      : the item has no recipe resources at all
  - truly isolated    : the item shares no resource with any other pool item
  - orphaned          : every partner was already consumed by an earlier group
  - partner available : the item still has a free partner, so it was excluded by
                        the acceptance budget rather than by reachability

Usage:
    uv run python scripts/challenge_coverage_gap.py [snapshot_version]
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.snapshot import load_snapshot
from processing.blocks.recipes import recipe_resource_ids
from processing.config import ProcessingConfig
from processing.experts.greedy_expert import GreedyGroupingExpert
from processing.metrics.group_metrics import GroupMetrics
from processing.orchestrator import RuneMaster
from processing.policy import GroupAcceptancePolicy
from processing.valuation.focus import break_density
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
    with contextlib.redirect_stderr(io.StringIO()):
        equipments, _, _ = load_snapshot(snapshot_dir)

    config = ProcessingConfig()
    excluded = set(config.excluded_resource_ids)

    # --- 1. Run the real pipeline. -------------------------------------------
    with contextlib.redirect_stdout(io.StringIO()):
        master = RuneMaster(equipments, config=config)
        groups = master.run_greedy()
    pool = master.equipments
    covered = {e.ankama_id for g in groups for e in g.get("equipments", [])}

    # --- 2. Replay the growth loop WITH the policy, to attribute the loss. ----
    objective = OverlapObjective(config.group_quality_weights)
    policy = GroupAcceptancePolicy(config)
    resources = {e.ankama_id: recipe_resource_ids(e) - excluded for e in pool}
    by_id = {e.ankama_id: e for e in pool}
    neighbours: dict[int, set[int]] = defaultdict(set)
    for eid, rids in resources.items():
        for rid in rids:
            neighbours[rid].add(eid)

    replay_covered: set[int] = set()
    singleton_seeds = 0
    rejected_by: dict[str, int] = defaultdict(int)
    for seed in sorted(pool, key=break_density, reverse=True):
        if seed.ankama_id in replay_covered or not resources[seed.ankama_id]:
            continue
        members = GreedyGroupingExpert._grow(
            seed, by_id, resources, neighbours, objective, config, excluded,
            replay_covered,
        )
        if len(members) < config.group_min_size:
            singleton_seeds += 1
            continue
        group = GroupMetrics.build_group_dict(
            members,
            excluded_resource_ids=excluded,
            quality_weights=config.group_quality_weights,
        )
        reason = policy.rejection_reason(group)
        if reason is not None:
            rejected_by[reason] += 1
            continue
        replay_covered |= {e.ankama_id for e in members}

    # --- 3. Classify the items the real run left uncovered. ------------------
    uncovered = [e for e in pool if e.ankama_id not in covered]
    empty_recipe = [e for e in uncovered if not resources[e.ankama_id]]
    isolated = [
        e for e in uncovered
        if resources[e.ankama_id]
        and not any(
            neighbours.get(rid, set()) - {e.ankama_id}
            for rid in resources[e.ankama_id]
        )
    ]
    rest = [e for e in uncovered if e not in empty_recipe and e not in isolated]
    orphaned, available = [], []
    for e in rest:
        partners: set[int] = set()
        for rid in resources[e.ankama_id]:
            partners |= neighbours.get(rid, set())
        partners -= {e.ankama_id}
        (orphaned if partners and partners <= covered else available).append(e)

    report = {
        "snapshot": snapshot_dir.name,
        "pool_size": len(pool),
        "groups": len(groups),
        "covered": len(covered),
        "coverage": len(covered) / len(pool) if pool else 0.0,
        "gap_attribution": {
            "singleton_seeds_below_min_size": singleton_seeds,
            "grown_but_policy_rejected": sum(rejected_by.values()),
            "rejected_by_reason": dict(sorted(rejected_by.items())),
        },
        "uncovered": len(uncovered),
        "uncovered_breakdown": {
            "empty_recipe": len(empty_recipe),
            "truly_isolated": len(isolated),
            "orphaned_all_partners_covered": len(orphaned),
            "partner_available_but_unassigned": len(available),
        },
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))

    # Sanity checks: a coverage claim that violates these is a bug, not a finding.
    assert report["covered"] <= report["pool_size"], "covered exceeds the pool"
    assert report["coverage"] <= 1.0, "coverage exceeds 100%"
    assert sum(report["uncovered_breakdown"].values()) == report["uncovered"], (
        "uncovered breakdown does not sum to the uncovered count"
    )

    out = ROOT / "data" / "plans" / "coverage-gap.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
