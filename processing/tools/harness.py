"""Offline method comparison for grouping experts.

Runs named methods offline and returns comparison rows for JSON persistence.
"""

import time
from typing import Any, Dict, List, Optional

from processing.config import ProcessingConfig
from processing.orchestrator import RuneMaster


METHODS = ("greedy",)


def _comparison_row(name: str, groups: list[dict[str, Any]], summary: dict[str, Any], runtime: float) -> dict[str, Any]:
    """Build a stable comparison row from a grouping result."""
    return {
        "method": name,
        "groups": summary.get("total_groups", 0),
        "unique_covered": summary.get("unique_equipment_in_groups", 0),
        "coverage_pct": round(summary.get("equipment_coverage_rate", 0.0) * 100, 2),
        "overlap_pct": round(summary.get("assignment_overlap_rate", 0.0) * 100, 2),
        "mean_group_size": round(summary.get("average_group_size", 0.0), 2),
        "mean_quality": round(summary.get("average_quality_score", 0.0), 4),
        "portfolio_quality": round(summary.get("portfolio_quality_score", 0.0), 4),
        "runtime_seconds": round(runtime, 3),
    }


def run_comparison(
    equipments,
    methods: tuple[str, ...] = METHODS,
    config: Optional[ProcessingConfig] = None,
    cache_manager=None,
) -> list[dict[str, Any]]:
    """Run named methods offline and return stable comparison rows."""
    rows = []
    for method in methods:
        method_config = config or ProcessingConfig()
        master = RuneMaster(equipments, method_config)
        started = time.perf_counter()
        groups = master.run_greedy()
        runtime = time.perf_counter() - started
        rows.append(_comparison_row(method, groups, master.get_summary(), runtime))
    return rows


def persist(rows: list[dict[str, Any]], path: str) -> None:
    """Persist a comparison table as deterministic, diffable JSON."""
    import json
    from pathlib import Path
    Path(path).write_text(json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")
