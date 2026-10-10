"""Offline baseline comparison harness."""

import json
import time
from pathlib import Path
from typing import Any

from models import Equipment
from processing.config import ProcessingConfig
from processing.orchestrator import RuneMaster


METHODS = ("deterministic", "random", "greedy", "hybrid")


def _comparison_row(name: str, groups: list[dict[str, Any]], summary: dict[str, Any], runtime: float) -> dict[str, Any]:
    return {
        "method": name,
        "group_count": len(groups),
        "group_sizes": sorted(len(group.get("equipments", [])) for group in groups),
        "line_items": sorted(group.get("unique_ingredients_count", 0) for group in groups),
        "mean_group_score": summary.get("average_quality_score", 0.0),
        "portfolio_score": summary.get("portfolio_quality_score", 0.0),
        "runtime_seconds": runtime,
    }


def run_comparison(
    equipments: list[Equipment],
    config: ProcessingConfig | None = None,
    methods: tuple[str, ...] = METHODS,
) -> list[dict[str, Any]]:
    """Run named methods offline and return stable comparison rows."""
    rows = []
    for method in methods:
        method_config = config or ProcessingConfig(random_seed=0)
        master = RuneMaster(equipments, method_config)
        started = time.perf_counter()
        if method == "deterministic":
            groups = master.run_deterministic()
        elif method == "random":
            groups = master.run_random_grouping()
        elif method == "greedy":
            groups = master.run_greedy()
        elif method == "hybrid":
            groups = master.run_hybrid_grouping()
        else:
            raise ValueError(f"Unknown comparison method: {method}")
        rows.append(_comparison_row(method, groups, master.get_summary(), time.perf_counter() - started))
    return rows


def write_comparison(path: str | Path, rows: list[dict[str, Any]]) -> None:
    """Persist a comparison table as deterministic, diffable JSON."""
    Path(path).write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")