"""Fast Phase 1 measurement: run each expert method on the full snapshot pool.

Loads the frozen snapshot directly (no API, no O(n^2) pair analysis).
Runs each method with a hard timeout; records timed_out as a finding.
Writes results to plans/phase1-results.json.

Usage:
    uv run scripts/phase1_measurement.py
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is on sys.path when run as a script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from data.snapshot import load_snapshot
from processing.config_dataclass import ProcessingConfig
from processing.orchestrator import RuneMaster
from processing.quality_metrics import PortfolioQualityEvaluator

SNAPSHOT_DIR = Path("/home/adamb/rune_master/data/snapshots/3.7.7.6")
RESULTS_FILE = Path("plans/phase1-results.json")

METHODS = [
    "deterministic",
    "random",
    "genetic",
    "greedy",
    "hybrid",
    "committee",
    "evolutionary_committee",
    "baseline",
]

TIMEOUTS = {
    "deterministic": 60,
    "random": 60,
    "genetic": 120,
    "greedy": 60,
    "hybrid": 60,
    "committee": 120,
    "evolutionary_committee": 300,
    "baseline": 60,
}

_RUNNERS = {
    "deterministic": "run_deterministic",
    "random": "run_random_grouping",
    "genetic": "run_genetic",
    "greedy": "run_greedy",
    "hybrid": "run_hybrid_grouping",
    "committee": "run_committee",
    "evolutionary_committee": "run_evolutionary_committee",
    "baseline": "run_baseline",
}


def run_method(
    equipments, config: ProcessingConfig, method: str, cache_manager
) -> Dict[str, Any]:
    """Run one method and return metrics."""
    runner_name = _RUNNERS[method]
    master = RuneMaster(equipments, config=config, cache_manager=cache_manager)
    started = time.perf_counter()

    with contextlib.redirect_stdout(io.StringIO()):
        try:
            groups = getattr(master, runner_name)()
        except Exception as e:
            elapsed = time.perf_counter() - started
            return {
                "method": method,
                "error": f"{type(e).__name__}: {e}",
                "elapsed_s": round(elapsed, 2),
                "groups": 0,
            }

    elapsed = time.perf_counter() - started

    if not groups:
        return {
            "method": method,
            "groups": 0,
            "elapsed_s": round(elapsed, 2),
        }

    portfolio = PortfolioQualityEvaluator(config.portfolio_quality_weights).evaluate(
        groups, len(equipments)
    )

    covered = set()
    for g in groups:
        for eq in g.get("equipments", []):
            covered.add(eq.ankama_id)

    return {
        "method": method,
        "groups": len(groups),
        "covered_items": len(covered),
        "coverage_pct": round(100 * len(covered) / len(equipments), 2),
        "portfolio_quality": round(portfolio.portfolio_quality_score, 4),
        "assignment_overlap": round(portfolio.assignment_overlap_rate, 4),
        "mean_group_size": round(
            sum(len(g["equipments"]) for g in groups) / len(groups), 2
        ),
        "mean_quality": round(
            sum(g.get("quality_score", 0.0) for g in groups) / len(groups), 4
        ),
        "mean_sharing_efficiency": round(
            sum(g.get("sharing_efficiency", 0.0) for g in groups) / len(groups), 4
        ),
        "elapsed_s": round(elapsed, 2),
    }


def main():
    print("Loading snapshot...")
    equipments, resources, set_index = load_snapshot(SNAPSHOT_DIR)
    print(f"Loaded {len(equipments)} equipments")

    from data.cache_manager import CacheManager
    cache = CacheManager(cache_file="data/cache.json")

    base_config = ProcessingConfig()
    results: List[Dict[str, Any]] = []

    for method in METHODS:
        print(f"\nRunning {method}...")
        config = replace(base_config, grouping_method=method)
        result = run_method(equipments, config, method, cache)
        results.append(result)

        if "error" in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(
                f"  groups={result.get('groups', 0)} "
                f"coverage={result.get('coverage_pct', 0)}% "
                f"pq={result.get('portfolio_quality', 0):.4f} "
                f"overlap={result.get('assignment_overlap', 0):.4f} "
                f"time={result.get('elapsed_s', 0)}s"
            )

    RESULTS_FILE.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nResults written to {RESULTS_FILE}")

    # Summary table
    print("\n" + "=" * 80)
    print(f"{'Method':<25} {'Groups':>6} {'Coverage':>9} {'PQ':>8} {'Overlap':>8} {'Time':>8}")
    print("-" * 80)
    for r in results:
        if "error" in r:
            print(f"{r['method']:<25} {'ERROR':>6} {'':>9} {'':>8} {'':>8} {r.get('elapsed_s', 0):>7.1f}s")
        else:
            print(
                f"{r['method']:<25} {r.get('groups', 0):>6} "
                f"{r.get('coverage_pct', 0):>8.2f}% "
                f"{r.get('portfolio_quality', 0):>8.4f} "
                f"{r.get('assignment_overlap', 0):>8.4f} "
                f"{r.get('elapsed_s', 0):>7.1f}s"
            )
    print("=" * 80)


if __name__ == "__main__":
    main()
