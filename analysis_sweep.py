"""Map pool and graph structure across level bands and crafts.

Characterises the raw material the grouping experts work with: how many items
exist, how many belong to a panoplie, how much resource sharing is actually
available, and what the similarity graph looks like once built. Expert runs are
opt-in because they are only meaningful once the structure is understood.

Usage:
    uv run analysis_sweep.py
    uv run analysis_sweep.py --with-experts --methods deterministic,committee
    uv run analysis_sweep.py --bands 1-50,50-100 --crafts bijoutier,forgeron
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import statistics
import time
from collections import Counter
from dataclasses import replace
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

import community as community_louvain
import networkx as nx

from config import (
    BIJOUTIER,
    CORDONNIER,
    FACONNEUR,
    FORGERON,
    SCULPTEUR,
    TAILLEUR,
    Config,
)
from data.api_client import DofusAPIClient
from data.cache_manager import CacheManager
from data.loaders import EquipmentLoader
from models import Equipment
from processing.blocks.recipes import recipe_resource_ids
from processing.blocks.similarity import jaccard
from processing.community_detector import CommunityDetector
from processing.config_dataclass import ProcessingConfig
from processing.graph_builder import GraphBuilder
from processing.orchestrator import RuneMaster
from processing.quality_metrics import PortfolioQualityEvaluator
from processing.valuation.focus import break_density

CRAFTS: Dict[str, List[str]] = {
    "cordonnier": CORDONNIER,
    "bijoutier": BIJOUTIER,
    "tailleur": TAILLEUR,
    "forgeron": FORGERON,
    "sculpteur": SCULPTEUR,
    "faconneur": FACONNEUR,
}

DEFAULT_BANDS: List[Tuple[int, int]] = [(1, 50), (50, 100), (100, 150), (150, 200)]

DEFAULT_METHODS: List[str] = [
    "deterministic",
    "random",
    "genetic",
    "hybrid",
    "committee",
    "evolutionary_committee",
]

_METHOD_DISPATCH = {
    "deterministic": "run_deterministic",
    "random": "run_random_grouping",
    "genetic": "run_genetic",
    "hybrid": "run_hybrid_grouping",
    "committee": "run_committee",
    "evolutionary_committee": "run_evolutionary_committee",
    "baseline": "run_baseline",
}

SHARE_THRESHOLDS = (1, 2, 3)


def _mean(values: Sequence[float]) -> float:
    return statistics.mean(values) if values else 0.0


def _median(values: Sequence[float]) -> float:
    return statistics.median(values) if values else 0.0


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(int(q * len(ordered)), len(ordered) - 1)]


def _set_pair_kind(left: Equipment, right: Equipment) -> str:
    """Classify a pair by panoplie membership."""
    if left.set_id is None and right.set_id is None:
        return "free_free"
    if left.set_id is None or right.set_id is None:
        return "free_set"
    return "same_set" if left.set_id == right.set_id else "cross_set"


def analyse_pool(equipments: List[Equipment]) -> Dict[str, Any]:
    """Describe pool composition, recipe shape, and panoplie membership."""
    resources = {e.ankama_id: recipe_resource_ids(e) for e in equipments}
    in_set = [e for e in equipments if e.set_id is not None]
    set_free = [e for e in equipments if e.set_id is None]

    usage: Counter[int] = Counter()
    for resource_ids in resources.values():
        usage.update(resource_ids)

    recipe_sizes = [len(resource_ids) for resource_ids in resources.values()]
    densities = [break_density(e) for e in equipments]
    set_sizes = Counter(e.set_id for e in in_set)

    return {
        "items": len(equipments),
        "items_in_set": len(in_set),
        "items_set_free": len(set_free),
        "set_free_pct": 100 * len(set_free) / len(equipments) if equipments else 0.0,
        "distinct_sets": len(set_sizes),
        "mean_set_members_present": _mean(list(set_sizes.values())),
        "distinct_resources": len(usage),
        "mean_recipe_size": _mean(recipe_sizes),
        "median_recipe_size": _median(recipe_sizes),
        "resources_used_once": sum(1 for c in usage.values() if c == 1),
        "resources_used_2plus": sum(1 for c in usage.values() if c >= 2),
        "resources_used_3plus": sum(1 for c in usage.values() if c >= 3),
        "max_resource_frequency": max(usage.values(), default=0),
        "break_density_mean_in_set": _mean([break_density(e) for e in in_set]),
        "break_density_mean_set_free": _mean([break_density(e) for e in set_free]),
        "break_density_median_in_set": _median([break_density(e) for e in in_set]),
        "break_density_median_set_free": _median([break_density(e) for e in set_free]),
        "top_decile_set_free_share": (
            sum(
                1
                for e in sorted(equipments, key=break_density, reverse=True)[
                    : max(len(equipments) // 10, 1)
                ]
                if e.set_id is None
            )
            / max(len(equipments) // 10, 1)
            if equipments
            else 0.0
        ),
        "break_density_p90": _quantile(densities, 0.9),
    }


def analyse_pairs(equipments: List[Equipment]) -> Dict[str, Any]:
    """Count resource-sharing pairs by threshold and panoplie relationship."""
    resources = {e.ankama_id: recipe_resource_ids(e) for e in equipments}
    result: Dict[str, Any] = {"total_pairs": 0, "mean_jaccard": 0.0}
    buckets: Dict[int, Counter[str]] = {t: Counter() for t in SHARE_THRESHOLDS}
    similarities: List[float] = []
    total_pairs = 0

    for left, right in combinations(equipments, 2):
        total_pairs += 1
        left_res = resources[left.ankama_id]
        right_res = resources[right.ankama_id]
        shared = len(left_res & right_res)
        similarities.append(jaccard(left_res, right_res))
        if shared:
            kind = _set_pair_kind(left, right)
            for threshold in SHARE_THRESHOLDS:
                if shared >= threshold:
                    buckets[threshold][kind] += 1
                    buckets[threshold]["total"] += 1

    result["total_pairs"] = total_pairs
    result["mean_jaccard"] = _mean(similarities)
    for threshold in SHARE_THRESHOLDS:
        bucket = buckets[threshold]
        total = bucket["total"]
        result[f"pairs_shared_ge{threshold}"] = total
        for kind in ("same_set", "cross_set", "free_set", "free_free"):
            result[f"pairs_shared_ge{threshold}_{kind}"] = bucket[kind]
        result[f"pairs_shared_ge{threshold}_same_set_pct"] = (
            100 * bucket["same_set"] / total if total else 0.0
        )
    return result


def analyse_graph(
    equipments: List[Equipment], config: ProcessingConfig
) -> Dict[str, Any]:
    """Describe the similarity graph and its Louvain partition."""
    graph, resources = GraphBuilder.build_equipment_graph(
        equipments,
        min_shared_ratio=config.graph_min_shared_ratio,
        min_shared_count=config.graph_min_shared_count,
        min_component_size=config.graph_min_component_size,
        same_set_edge_discount=config.same_set_edge_discount,
    )
    by_id = {e.ankama_id: e for e in equipments}
    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()

    if node_count == 0:
        return {
            "graph_nodes": 0,
            "graph_edges": 0,
            "graph_retained_pct": 0.0,
            "graph_density": 0.0,
            "graph_components": 0,
            "graph_largest_component": 0,
            "graph_same_set_edge_pct": 0.0,
            "communities": 0,
            "community_mean_size": 0.0,
            "community_max_size": 0,
            "modularity": 0.0,
            "community_mean_largest_set_share": 0.0,
            "community_pure_panoplie_pct": 0.0,
        }

    same_set_edges = sum(
        1 for _, _, data in graph.edges(data=True) if data.get("same_set")
    )
    components = list(nx.connected_components(graph))

    with contextlib.redirect_stdout(io.StringIO()):
        partition = CommunityDetector.find_best_louvain_partition(
            graph, resources, resolution_range=config.resolution_range, random_seed=42
        )
    grouped: Dict[int, List[int]] = {}
    for equipment_id, community_id in partition.items():
        grouped.setdefault(community_id, []).append(equipment_id)

    set_shares: List[float] = []
    for members in grouped.values():
        counts = Counter(
            by_id[m].set_id for m in members if by_id.get(m) and by_id[m].set_id is not None
        )
        set_shares.append(max(counts.values(), default=0) / len(members))

    return {
        "graph_nodes": node_count,
        "graph_edges": edge_count,
        "graph_retained_pct": 100 * node_count / len(equipments) if equipments else 0.0,
        "graph_density": nx.density(graph),
        "graph_components": len(components),
        "graph_largest_component": max((len(c) for c in components), default=0),
        "graph_same_set_edge_pct": 100 * same_set_edges / edge_count if edge_count else 0.0,
        "communities": len(grouped),
        "community_mean_size": _mean([len(m) for m in grouped.values()]),
        "community_max_size": max((len(m) for m in grouped.values()), default=0),
        "modularity": community_louvain.modularity(partition, graph),
        "community_mean_largest_set_share": _mean(set_shares),
        "community_pure_panoplie_pct": (
            100 * sum(1 for s in set_shares if s >= 0.8) / len(set_shares)
            if set_shares
            else 0.0
        ),
    }


def analyse_expert_run(
    equipments: List[Equipment],
    config: ProcessingConfig,
    method: str,
    cache: CacheManager,
) -> Dict[str, Any]:
    """Run one grouping method and summarise the portfolio it produces."""
    runner = _METHOD_DISPATCH[method]
    master = RuneMaster(equipments, config=config, cache_manager=cache)
    started = time.perf_counter()
    # Experts are chatty; the sweep keeps its own log.
    with contextlib.redirect_stdout(io.StringIO()):
        groups = getattr(master, runner)()
    elapsed = time.perf_counter() - started

    if not groups:
        return {"method": method, "groups": 0, "elapsed_s": round(elapsed, 2)}

    set_shares, free_ratios = [], []
    for group in groups:
        set_ids = [e.set_id for e in group["equipments"]]
        free_ratios.append(sum(1 for s in set_ids if s is None) / len(set_ids))
        counts = Counter(s for s in set_ids if s is not None)
        set_shares.append(max(counts.values(), default=0) / len(set_ids))

    portfolio = PortfolioQualityEvaluator(config.portfolio_quality_weights).evaluate(
        groups, len(equipments)
    )
    return {
        "method": method,
        "groups": len(groups),
        "mean_group_size": _mean([len(g["equipments"]) for g in groups]),
        "mean_quality": _mean([g.get("quality_score", 0.0) for g in groups]),
        "mean_sharing_efficiency": _mean(
            [g.get("sharing_efficiency", 0.0) for g in groups]
        ),
        "portfolio_quality": portfolio.portfolio_quality_score,
        "equipment_coverage": portfolio.equipment_coverage_rate,
        "assignment_overlap": portfolio.assignment_overlap_rate,
        "mean_largest_set_share": _mean(set_shares),
        "mean_set_free_ratio": _mean(free_ratios),
        "mostly_panoplie_groups": sum(1 for s in set_shares if s >= 0.8),
        "elapsed_s": round(elapsed, 2),
    }


def load_pool(
    cache: CacheManager,
    api: DofusAPIClient,
    set_index: Dict[int, int],
    item_types: List[str],
    min_level: int,
    max_level: int,
) -> List[Equipment]:
    """Fetch one band/craft slice of the equipment pool."""
    loader = EquipmentLoader(cache=cache, set_index=set_index)
    with contextlib.redirect_stdout(io.StringIO()):
        raw = api.get_all_equipments(
            item_types=item_types, min_level=min_level, max_level=max_level
        )
        return loader.from_raw_batch(raw)


def _parse_bands(value: str) -> List[Tuple[int, int]]:
    bands = []
    for chunk in value.split(","):
        low, _, high = chunk.strip().partition("-")
        bands.append((int(low), int(high)))
    return bands


def _parse_list(value: str, valid: Iterable[str], label: str) -> List[str]:
    items = [v.strip() for v in value.split(",") if v.strip()]
    unknown = sorted(set(items) - set(valid))
    if unknown:
        raise SystemExit(f"Unknown {label}: {', '.join(unknown)}")
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bands", default="1-50,50-100,100-150,150-200")
    parser.add_argument("--crafts", default=",".join(CRAFTS))
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    parser.add_argument("--with-experts", action="store_true")
    parser.add_argument("--out", default="analysis")
    args = parser.parse_args()

    bands = _parse_bands(args.bands)
    crafts = _parse_list(args.crafts, CRAFTS, "craft")
    methods = _parse_list(args.methods, _METHOD_DISPATCH, "method")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")

    cache = CacheManager(cache_file=Config.CACHE_FILE)
    api = DofusAPIClient()
    set_index = cache.get_equipment_set_index()
    if not set_index:
        set_index = api.get_equipment_set_index()
        if set_index:
            cache.set_equipment_set_index(set_index)

    base_config = ProcessingConfig()
    structure_rows: List[Dict[str, Any]] = []
    expert_rows: List[Dict[str, Any]] = []

    print(f"Sweeping {len(bands)} bands x {len(crafts)} crafts")
    for min_level, max_level in bands:
        for craft in crafts:
            label = f"{min_level:3d}-{max_level:3d} {craft:11s}"
            pool = load_pool(
                cache, api, set_index, CRAFTS[craft], min_level, max_level
            )
            if not pool:
                print(f"{label} | empty pool")
                continue

            row: Dict[str, Any] = {
                "min_level": min_level,
                "max_level": max_level,
                "craft": craft,
            }
            row.update(analyse_pool(pool))
            row.update(analyse_pairs(pool))
            row.update(analyse_graph(pool, base_config))
            structure_rows.append(row)

            print(
                f"{label} | items={row['items']:3d} "
                f"set-free={row['set_free_pct']:4.0f}% "
                f"pairs>=3={row['pairs_shared_ge3']:4d} "
                f"(same-set {row['pairs_shared_ge3_same_set_pct']:4.0f}%) "
                f"graph={row['graph_nodes']:3d}n/{row['graph_edges']:4d}e "
                f"comms={row['communities']:3d} "
                f"purity={row['community_mean_largest_set_share']:.2f}"
            )

            if not args.with_experts:
                continue
            for method in methods:
                config = replace(base_config, grouping_method=method)
                try:
                    result = analyse_expert_run(pool, config, method, cache)
                except Exception as error:  # one bad method must not kill the sweep
                    result = {"method": method, "error": f"{type(error).__name__}: {error}"}
                result.update(
                    {"min_level": min_level, "max_level": max_level, "craft": craft}
                )
                expert_rows.append(result)
                if "error" in result:
                    print(f"{label} | {method:22s} FAILED {result['error']}")
                else:
                    print(
                        f"{label} | {method:22s} groups={result['groups']:3d} "
                        f"pq={result['portfolio_quality']:.3f} "
                        f"cov={result['equipment_coverage']:.2f} "
                        f"setshare={result['mean_largest_set_share']:.2f} "
                        f"{result['elapsed_s']:.1f}s"
                    )

    _write(out_dir / f"structure-{stamp}", structure_rows)
    if expert_rows:
        _write(out_dir / f"experts-{stamp}", expert_rows)
    cache.close()


def _write(base: Path, rows: List[Dict[str, Any]]) -> None:
    """Write rows as both JSON and CSV."""
    base.with_suffix(".json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    fieldnames: List[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with base.with_suffix(".csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"→ {base.with_suffix('.json')} / {base.with_suffix('.csv')}")


if __name__ == "__main__":
    main()
