"""Parallel parameter grid search for the greedy grouping method."""
import multiprocessing
import os
import time
from dataclasses import replace
from typing import Any, Dict, Tuple

from processing.config import ProcessingConfig
from processing.orchestrator import RuneMaster


class ParameterTuner:
    """Grid-search graph_min_shared_ratio and group_min_shared_resources."""

    def __init__(self, method: str = "greedy"):
        self.method = method

    def _evaluate(self, params: tuple) -> Tuple[float, Dict[str, Any], ProcessingConfig]:
        """Evaluate a single configuration."""
        ratio, count, equipments, cache_manager = params
        config = ProcessingConfig(
            group_min_shared_resources=count,
            grouping_method=self.method,
        )
        master = RuneMaster(equipments, config=config, cache_manager=cache_manager)
        groups = master.run_greedy()
        if not groups:
            return 0.0, {}, config
        stats = master.get_summary()
        score = float(stats.get("portfolio_quality_score", 0.0))
        return score, stats, config

    def tune(self, equipments, cache_manager=None) -> Tuple[ProcessingConfig, Dict[str, Any]]:
        """Run a parallel grid search to find the best parameters."""
        print(f"\n🧪 [Tuner] Starting PARALLEL parameter search for method: {self.method}")

        ratios = [0.15, 0.20, 0.25, 0.30]
        counts = [2, 3, 4]
        workers = min(multiprocessing.cpu_count(), 8)
        configs = [(r, c, equipments, cache_manager) for r in ratios for c in counts]

        start = time.time()
        with multiprocessing.Pool(workers) as pool:
            results = pool.map(self._evaluate, configs)

        best_score = -1.0
        best_stats: Dict[str, Any] = {}
        best_config_params: tuple = (0.15, 3)

        for score, stats, config in results:
            if score > best_score:
                best_score = score
                best_stats = stats
                best_config_params = (config.group_min_shared_resources,)

        elapsed = time.time() - start
        print(f"\n✅ [Tuner] Best score: {best_score:.4f} ({elapsed:.1f}s)")
        print(f"   Min shared resources: {best_config_params[0]}")

        ratio, count = best_config_params
        best_config = ProcessingConfig(
            group_min_shared_resources=count,
            grouping_method=self.method,
        )
        return best_config, best_stats
