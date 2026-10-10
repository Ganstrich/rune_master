"""Parameter tuning engine for the RuneMaster pipeline.

Iterates through different configuration combinations and evaluates
them against a multi-objective quality function to find the 'Golden Config'.
"""

import concurrent.futures
import itertools
from typing import Any, Dict, List, Optional, Tuple

from models import Equipment
from processing.config import ProcessingConfig
from processing.orchestrator import RuneMaster


def _worker_run_config(
    equipments: List[Equipment],
    ratio: float,
    count: int,
    method: str,
    cache_file: str,
) -> Tuple[float, float, int, float, Dict[str, Any]]:
    """Standalone worker function to run a single configuration in a separate process.

    Returns: (score, ratio, count, retention, stats)
    """
    from data.cache_manager import CacheManager

    # Initialize process-local cache manager (read-only)
    cache_manager = CacheManager(cache_file=cache_file)

    config = ProcessingConfig(
        graph_min_shared_ratio=ratio,
        group_min_shared_resources=count,
        grouping_method=method,
        use_density_filtering=True,
        equipment_density_level_ratio=1.5,  # Relaxed for tuning
        random_seed=0,
    )

    # Run the master
    master = RuneMaster(equipments, config=config, cache_manager=cache_manager)

    if method == "deterministic":
        master.run_deterministic()
    elif method == "random":
        master.run_random_grouping()
    elif method == "greedy":
        master.run_greedy()
    elif method == "hybrid":
        master.run_hybrid_grouping()
    else:
        master.run_all()

    stats = master.get_summary()

    # Use the static scoring logic
    score = ParameterTuner.evaluate_quality(stats)

    return (score, ratio, count, stats.get("retention_rate", 0.0), stats)


class ParameterTuner:
    """Tuner that searches for optimal grouping parameters using parallel execution."""

    def __init__(
        self, equipments: List[Equipment], cache_manager=None, api_client=None
    ):
        self.equipments = equipments
        self.cache_manager = cache_manager
        self.api_client = api_client

    @staticmethod
    def evaluate_quality(stats: Dict[str, Any]) -> float:
        """Return the canonical overlap-aware portfolio quality score."""
        if not stats or stats.get("total_groups", 0) == 0:
            return 0.0
        return float(stats.get("portfolio_quality_score", 0.0))

    def tune(
        self, method: str = "deterministic"
    ) -> Tuple[ProcessingConfig, Dict[str, Any]]:
        """Run a parallel grid search to find the best parameters."""
        print(f"\n🧪 [Tuner] Starting PARALLEL parameter search for method: {method}")

        # Define the search space
        ratios = [0.15, 0.2, 0.25, 0.3]
        counts = [2, 3, 4]
        combinations = list(itertools.product(ratios, counts))

        best_score = -1.0
        best_config_params = None
        best_stats = None

        cache_file = (
            self.cache_manager.cache_file if self.cache_manager else "resource_cache.db"
        )

        # Execute combinations in parallel
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(
                    _worker_run_config, self.equipments, r, c, method, cache_file
                )
                for r, c in combinations
            ]

            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                try:
                    score, ratio, count, retention, stats = future.result()
                    max_s = stats.get("max_group_size", 0)
                    print(
                        f"      [{i}/{len(combinations)}] Ratio: {ratio:.2f}, MinItems: {count} => Score: {score:.2f} (Ret: {retention:.1%}, MaxSize: {max_s})"
                    )

                    if score > best_score:
                        best_score = score
                        best_config_params = (ratio, count)
                        best_stats = stats
                except Exception as e:
                    print(f"      [!] Configuration failed: {e}")

        if not best_config_params:
            print("⚠️ [Tuner] No valid configurations found. Using defaults.")
            return ProcessingConfig(), {}

        ratio, count = best_config_params
        best_config = ProcessingConfig(
            graph_min_shared_ratio=ratio,
            group_min_shared_resources=count,
            grouping_method=method,
        )

        print(f"\n🏆 [Tuner] Best Configuration Found!")
        print(f"      Score: {best_score:.2f}")
        print(f"      Ratio: {ratio:.2f}")
        print(f"      Min Shared Items: {count}")
        print(f"      Max Group Size: {best_stats.get('max_group_size')}")

        return best_config, best_stats
