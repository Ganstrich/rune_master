#!/usr/bin/env python3
"""Run every grouping method and expert through the challenge metrics.

Implements plans/pipeline-challenge.md §4. API-only: no prices, no taux, no
rarity. Each method runs in a subprocess with a hard timeout, because the full
committee run was observed to exceed 550s -- a method that cannot finish on the
full pool is a finding, not an error to hide.

Usage:
    uv run python scripts/challenge_evaluate.py
    uv run python scripts/challenge_evaluate.py --methods greedy,baseline
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import Config
from data.snapshot import load_snapshot
from processing.challenge_metrics import (
    evaluate_portfolio,
    resource_breadth,
    resource_pods,
)
from processing.config_dataclass import ProcessingConfig
from processing.equipment_filter import SetExclusionFilter

METHODS = (
    "deterministic",
    "random",
    "hybrid",
    "committee",
    "genetic",
    "greedy",
    "evolutionary_committee",
    "survey",
)

EXPERTS = ("deterministic", "random", "genetic", "baseline", "greedy")

# Independent, single-process wall-clock budgets.
METHOD_TIMEOUT = 900
EXPERT_TIMEOUT = 900


def resolve_snapshot(version: str | None) -> Path:
    """Return the snapshot directory for a version, or the only one present."""
    base = ROOT / "data" / "snapshots"
    if version:
        return base / version
    available = sorted(p for p in base.iterdir() if p.is_dir())
    if not available:
        raise SystemExit("No snapshots found under data/snapshots/")
    return available[-1]


def raw_resources_by_id(snapshot_dir: Path) -> dict[int, dict]:
    """Read raw resource records straight from the snapshot DB."""
    import sqlite3

    conn = sqlite3.connect(str(snapshot_dir / "snapshot.db"))
    try:
        rows = conn.execute("SELECT id, data FROM resources").fetchall()
    finally:
        conn.close()
    return {int(resource_id): json.loads(payload) for resource_id, payload in rows}


def raw_equipment_recipes(snapshot_dir: Path) -> dict[int, list[dict]]:
    """Read raw recipe entry lists straight from the snapshot DB."""
    import sqlite3

    conn = sqlite3.connect(str(snapshot_dir / "snapshot.db"))
    try:
        rows = conn.execute("SELECT id, data FROM equipment").fetchall()
    finally:
        conn.close()
    return {
        int(equipment_id): json.loads(payload).get("recipe", [])
        for equipment_id, payload in rows
    }


def run_in_subprocess(target: str, mode: str, timeout: int) -> tuple[list[dict] | None, dict]:
    """Run one method or expert in a fresh process and capture its groups.

    A timeout is recorded as ``timed_out`` rather than raised: a method that
    cannot finish on the full pool is itself a finding (plan §4).
    """
    flag = "--method" if mode == "method" else "--expert"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "challenge_worker.py"),
        "--snapshot", str(SNAPSHOT_DIR),
        flag, target,
    ]

    started = time.time()
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT)
        )
    except subprocess.TimeoutExpired:
        return None, {
            "status": "timed_out",
            "elapsed": round(time.time() - started, 2),
            "timeout": timeout,
        }

    payloads = [
        line[len("@@RESULT@@"):]
        for line in completed.stdout.splitlines()
        if line.startswith("@@RESULT@@")
    ]
    if not payloads:
        return None, {
            "status": "failed",
            "elapsed": round(time.time() - started, 2),
            "exit_code": completed.returncode,
            "stderr_tail": completed.stderr[-2000:],
        }
    return json.loads(payloads[-1]), {
        "status": "completed",
        "elapsed": round(time.time() - started, 2),
        "exit_code": completed.returncode,
    }


def main() -> int:
    global SNAPSHOT_DIR

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=None, help="Snapshot version")
    parser.add_argument("--methods", default="all", help="Comma list, or 'all'")
    parser.add_argument("--experts", default="all", help="Comma list, or 'all'")
    parser.add_argument(
        "--timeout",
        type=int,
        default=METHOD_TIMEOUT,
        help="Per-run wall-clock budget in seconds",
    )
    args = parser.parse_args()

    snapshot_dir = resolve_snapshot(args.version)
    SNAPSHOT_DIR = snapshot_dir
    print(f"Snapshot: {snapshot_dir}")

    equipments, resources, set_index = load_snapshot(snapshot_dir)
    print(f"Loaded {len(equipments)} equipment, {len(resources)} resources")

    raw_resources = raw_resources_by_id(snapshot_dir)
    raw_recipes = raw_equipment_recipes(snapshot_dir)
    breadth = resource_breadth(equipments)
    pods = resource_pods(raw_resources)

    equipment_by_id = {int(e.ankama_id): e for e in equipments}
    excluded = frozenset(ProcessingConfig().excluded_resource_ids)

    methods = METHODS if args.methods == "all" else [
        name.strip() for name in args.methods.split(",") if name.strip()
    ]
    experts = EXPERTS if args.experts == "all" else [
        name.strip() for name in args.experts.split(",") if name.strip()
    ]

    def evaluate(group_payloads, pool, label):
        """Score a run whose groups reference equipment ids only."""
        memberships = []
        for payload in group_payloads or []:
            members = [equipment_by_id[i] for i in payload["equipments"]
                       if i in equipment_by_id]
            if members:
                memberships.append(members)
        return evaluate_portfolio(
            [{"equipments": members} for members in memberships],
            pool,
            breadth=breadth,
            pods=pods,
            raw_recipes=raw_recipes,
            excluded=excluded,
        )

    results: dict[str, dict] = {}

    # Methods run against the set-excluded pool, which is what the pipeline sees.
    from processing.equipment_filter import SetExclusionFilter

    pool, _ = SetExclusionFilter.exclude_panoplie_items(
        equipments, ProcessingConfig().set_exclusion_min_size
    )
    print(f"Set-excluded pool: {len(pool)}")

    for name in methods:
        print(f"\n=== method: {name} ===", flush=True)
        payloads, meta = run_in_subprocess(name, "method", args.timeout)
        if payloads is None:
            print(f"  {meta['status']} ({meta['elapsed']}s)")
            results[name] = {"status": meta["status"], "meta": meta}
            continue
        report = evaluate(payloads, pool, name)
        report["meta"] = meta
        results[name] = report
        print(f"  {meta['status']} in {meta['elapsed']}s | "
              f"{report['group_count']} groups | "
              f"coverage {report['coverage']['global'] * 100:.2f}%")

    for name in experts:
        print(f"\n=== expert: {name} ===", flush=True)
        payloads, meta = run_in_subprocess(name, "expert", args.timeout)
        if payloads is None:
            print(f"  {meta['status']} ({meta['elapsed']}s)")
            results[f"expert:{name}"] = {"status": meta["status"], "meta": meta}
            continue
        report = evaluate(payloads, pool, name)
        report["meta"] = meta
        results[f"expert:{name}"] = report
        print(f"  {meta['status']} in {meta['elapsed']}s | "
              f"{report['group_count']} groups | "
              f"coverage {report['coverage']['global'] * 100:.2f}%")

    out_path = ROOT / "plans" / "challenge-results.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
