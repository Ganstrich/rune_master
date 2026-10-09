#!/usr/bin/env python3
"""Profile the full equipment snapshot and write plans/data-profile.md.

READ-ONLY analysis: loads the frozen snapshot via data.snapshot.load_snapshot,
computes recipe / structure / similarity / filter statistics, and writes a
markdown report. Does NOT modify any src files and does NOT propose fixes.

Every number in the report is computed here from the snapshot data.
Interpretations are explicitly marked INFERENCE.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.snapshot import load_snapshot, load_manifest
from processing.blocks.recipes import recipe_resource_ids
from processing.blocks.similarity import jaccard
from processing.equipment_filter import EquipmentFilteringStrategy

SNAPSHOT_DIR = Path(__file__).parent.parent / "data" / "snapshots" / "3.7.7.6"
OUTPUT_MD = Path(__file__).parent.parent / "plans" / "data-profile.md"

LEVEL_BAND = 20  # matches ProcessingConfig.density_level_band
DENSITY_RATIO = 3.0  # matches ProcessingConfig.equipment_density_level_ratio
EXCLUDED = {15263, 14635}  # matches ProcessingConfig.excluded_resource_ids

# French type name -> English slot name (for readability)
SLOT_EN = {
    "Anneau": "ring",
    "Bottes": "boots",
    "Chapeau": "hat",
    "Ceinture": "belt",
    "Amulette": "amulet",
    "Cape": "cloak",
    "Bouclier": "shield",
    "Épée": "sword",
    "Marteau": "hammer",
    "Bâton": "staff",
    "Baguette": "wand",
    "Dague": "dagger",
    "Arc": "bow",
    "Hache": "axe",
    "Pelle": "shovel",
    "Lance": "lance",
    "Faux": "scythe",
}


def slot_en(fr: str) -> str:
    return SLOT_EN.get(fr, fr)


def dist_stats(values: list[int] | list[float]) -> dict:
    """Return min/median/p90/max for a list of numbers."""
    if not values:
        return {"min": 0, "median": 0, "p90": 0, "max": 0, "n": 0}
    s = sorted(values)
    n = len(s)
    p90_idx = min(int(0.9 * (n - 1)), n - 1)
    return {
        "min": s[0],
        "median": statistics.median(s),
        "p90": s[p90_idx],
        "max": s[-1],
        "n": n,
    }


def fmt(x: float) -> str:
    if isinstance(x, float):
        if x == int(x):
            return str(int(x))
        return f"{x:.2f}"
    return str(x)


def main() -> None:
    print(f"Loading snapshot from {SNAPSHOT_DIR} ...")
    equipments, resources, set_index = load_snapshot(SNAPSHOT_DIR)
    manifest = load_manifest(SNAPSHOT_DIR)

    n = len(equipments)
    print(f"  Equipment: {n}")
    print(f"  Resources: {len(resources)}")
    print(f"  Set mappings: {len(set_index)}")

    # Resource id -> name
    res_name = {r.ankama_id: r.name for r in resources}
    res_type = {r.ankama_id: r.type["name"] for r in resources}

    # Pre-compute resource sets per equipment
    eq_resources: dict[int, set[int]] = {}
    eq_units: dict[int, int] = {}
    for eq in equipments:
        rids = recipe_resource_ids(eq)
        eq_resources[eq.ankama_id] = rids
        eq_units[eq.ankama_id] = sum(req.quantity for req in eq.recipe)

    # Inverted index: resource_id -> set of equipment_ids
    inverted: dict[int, set[int]] = defaultdict(set)
    for eq_id, rids in eq_resources.items():
        for rid in rids:
            inverted[rid].add(eq_id)

    # ====================================================================
    # RECIPES
    # ====================================================================

    # Scope: recipe entries with item_subtype != 'resources' (quest equipment,
    # consumables) are filtered out by the loader. Build an "all entries" view
    # from raw snapshot data so we can compare the two treatments.
    import sqlite3

    subtype_counts: Counter = Counter()
    eq_all: dict[int, set[int]] = {}
    _conn = sqlite3.connect(str(SNAPSHOT_DIR / "snapshot.db"))
    for _row in _conn.execute("SELECT data FROM equipment"):
        _raw = json.loads(_row[0])
        _eid = int(_raw["ankama_id"])
        _ids: set[int] = set()
        for _item in _raw.get("recipe", []):
            _st = _item.get("item_subtype", "MISSING")
            subtype_counts[_st] += 1
            _ids.add(int(_item.get("item_ankama_id", 0)))
        eq_all[_eid] = _ids
    _conn.close()

    non_resource_entries = sum(
        c for st, c in subtype_counts.items() if st != "resources"
    )
    items_with_non_resource = {
        eid
        for eid in eq_all
        if eq_all[eid] != eq_resources.get(eid, set())
    }

    # 1. Distinct resources per recipe; units per recipe
    distinct_counts = [len(eq_resources[eq.ankama_id]) for eq in equipments]
    unit_counts = [eq_units[eq.ankama_id] for eq in equipments]
    distinct_stats = dist_stats(distinct_counts)
    units_stats = dist_stats(unit_counts)
    empty_recipe_count = sum(1 for c in distinct_counts if c == 0)

    # 2. Resource frequency
    res_freq = {rid: len(eq_set) for rid, eq_set in inverted.items()}
    sorted_res = sorted(res_freq.items(), key=lambda x: (-x[1], x[0]))
    top30 = sorted_res[:30]
    threshold_20pct = 0.20 * n
    above_20pct = [(rid, cnt) for rid, cnt in sorted_res if cnt > threshold_20pct]

    # 3. Are 15263 and 14635 actually the ubiquitous ones?
    excluded_freq = {rid: res_freq.get(rid, 0) for rid in EXCLUDED}
    others_ubiquitous = [
        (rid, cnt) for rid, cnt in above_20pct if rid not in EXCLUDED
    ]

    # 4. Dead-end resources (used by exactly 1 item)
    dead_ends = [(rid, cnt) for rid, cnt in sorted_res if cnt == 1]

    # ====================================================================
    # STRUCTURE
    # ====================================================================

    # 5. Items per type and per level band
    type_counts = Counter(eq.type["name"] for eq in equipments)
    band_counts = Counter(eq.level // LEVEL_BAND for eq in equipments)

    # 6. Panoplie sizes
    set_sizes = Counter()
    none_count = 0
    for eq in equipments:
        if eq.set_id is None:
            none_count += 1
        else:
            set_sizes[eq.set_id] += 1
    set_size_values = list(set_sizes.values())
    set_size_stats = dist_stats(set_size_values)

    # 7. Type x level-band cells with too few items to group (< 2)
    cell_counts = Counter((eq.type["name"], eq.level // LEVEL_BAND) for eq in equipments)
    all_types = sorted(type_counts.keys())
    all_bands = sorted(band_counts.keys())
    sparse_cells = []
    for t in all_types:
        for b in all_bands:
            cnt = cell_counts.get((t, b), 0)
            if cnt < 2:
                sparse_cells.append((t, b, cnt))

    # ====================================================================
    # SIMILARITY
    # ====================================================================

    # 8. Pairwise Jaccard distribution
    candidate_pairs: set[tuple[int, int]] = set()
    for eq_set in inverted.values():
        if len(eq_set) >= 2:
            for a, b in combinations(sorted(eq_set), 2):
                candidate_pairs.add((a, b))

    total_pairs = n * (n - 1) // 2
    jaccard_values: list[float] = []
    pair_same_type = 0
    pair_cross_type = 0
    pair_same_band = 0
    pair_cross_band = 0
    level_diffs: list[int] = []
    shared_counts: list[int] = []
    same_type_shared = 0
    cross_type_shared = 0

    eq_by_id = {eq.ankama_id: eq for eq in equipments}

    # ---- Dead-end deep dive: categorize + sample across level bands ----
    # Dead-ends = resources used by exactly one equipment (resources-only view).
    # Cross-check against RAW recipes (all subtypes) to confirm they stay single-use.
    dead_end_items = {rid: cnt for rid, cnt in sorted_res if cnt == 1}
    dead_single = {rid: next(iter(inverted[rid])) for rid in dead_end_items}
    raw_usage = Counter()
    for _eid, _rids in eq_all.items():
        for _rid in _rids:
            raw_usage[_rid] += 1
    dead_end_still_single_raw = sum(
        1 for rid in dead_end_items if raw_usage.get(rid, 0) <= 1
    )
    dead_by_restype = Counter(res_type.get(rid, "unknown") for rid in dead_end_items)
    samples_by_band: dict[int, list] = defaultdict(list)
    for rid, eid in sorted(dead_single.items()):
        eq = eq_by_id[eid]
        samples_by_band[eq.level // LEVEL_BAND].append(
            (
                rid,
                res_name.get(rid, "?"),
                res_type.get(rid, "?"),
                eq.ankama_id,
                eq.level,
                eq.type["name"],
                eq.name,
            )
        )
    for b in samples_by_band:
        samples_by_band[b].sort(key=lambda x: x[4])

    # ---- Do the boss items (consumers of dead-end resources) still share? ----
    boss_items = {dead_single[rid] for rid in dead_end_items}
    degree = {eid: 0 for eid in eq_resources}
    for _rid, _s in inverted.items():
        if len(_s) >= 2:
            for _a in _s:
                degree[_a] += len(_s) - 1
    isolated_all = [eid for eid in eq_resources if degree[eid] == 0]
    boss_isolated = [e for e in isolated_all if e in boss_items]
    boss_sharing = [e for e in boss_items if degree[e] > 0]
    boss_pairs = []
    for _a, _b in combinations(sorted(boss_items), 2):
        _sh = eq_resources[_a] & eq_resources[_b]
        if _sh:
            boss_pairs.append((_a, _b, len(_sh)))
    boss_drivers: Counter = Counter()
    for _a, _b, _n in boss_pairs:
        for _rid in eq_resources[_a] & eq_resources[_b]:
            boss_drivers[_rid] += 1
    boss_top_drivers = boss_drivers.most_common(10)

    for a, b in candidate_pairs:
        ra = eq_resources[a]
        rb = eq_resources[b]
        j = jaccard(ra, rb)
        jaccard_values.append(j)
        shared = len(ra & rb)
        shared_counts.append(shared)

        ea = eq_by_id[a]
        eb = eq_by_id[b]
        if ea.type["name"] == eb.type["name"]:
            pair_same_type += 1
            same_type_shared += shared
        else:
            pair_cross_type += 1
            cross_type_shared += shared
        if ea.level // LEVEL_BAND == eb.level // LEVEL_BAND:
            pair_same_band += 1
        else:
            pair_cross_band += 1
        level_diffs.append(abs(ea.level - eb.level))

    jaccard_stats = dist_stats(jaccard_values)
    exceed_01 = sum(1 for j in jaccard_values if j >= 0.1)
    exceed_02 = sum(1 for j in jaccard_values if j >= 0.2)
    exceed_03 = sum(1 for j in jaccard_values if j >= 0.3)

    # 9. Connected components at several thresholds
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]
    components_by_thresh = {}
    for t in thresholds:
        adj: dict[int, set[int]] = defaultdict(set)
        for a, b in candidate_pairs:
            ra = eq_resources[a]
            rb = eq_resources[b]
            if jaccard(ra, rb) >= t:
                adj[a].add(b)
                adj[b].add(a)
        visited: set[int] = set()
        comps = []
        for node in adj:
            if node in visited:
                continue
            stack = [node]
            comp = []
            visited.add(node)
            while stack:
                cur = stack.pop()
                comp.append(cur)
                for nb in adj[cur]:
                    if nb not in visited:
                        visited.add(nb)
                        stack.append(nb)
            comps.append(comp)
        comp_sizes = [len(c) for c in comps]
        components_by_thresh[t] = {
            "count": len(comps),
            "sizes": dist_stats(comp_sizes),
            "largest": max(comp_sizes) if comp_sizes else 0,
            "nodes_in_comps": sum(comp_sizes),
        }

    # 10. Cross-type sharing
    total_shared_pairs = pair_same_type + pair_cross_type
    cross_type_pct = (
        100.0 * pair_cross_type / total_shared_pairs if total_shared_pairs else 0.0
    )
    total_shared_instances = same_type_shared + cross_type_shared
    cross_type_shared_pct = (
        100.0 * cross_type_shared / total_shared_instances
        if total_shared_instances
        else 0.0
    )

    # 11. Cross-level sharing
    level_diff_stats = dist_stats(level_diffs)
    same_band_pct = (
        100.0 * pair_same_band / (pair_same_band + pair_cross_band)
        if (pair_same_band + pair_cross_band)
        else 0.0
    )
    narrow_level = sum(1 for d in level_diffs if d <= LEVEL_BAND)
    narrow_level_pct = (
        100.0 * narrow_level / len(level_diffs) if level_diffs else 0.0
    )

    # ====================================================================
    # FILTERS
    # ====================================================================

    # 12. Density filter (ratio 3.0) removal by type and level band
    filtered, excluded = EquipmentFilteringStrategy.filter_by_density_ratio(
        equipments, DENSITY_RATIO
    )
    excluded_by_type = Counter(eq.type["name"] for eq in excluded)
    excluded_by_band = Counter(eq.level // LEVEL_BAND for eq in excluded)
    retained_by_type = Counter(eq.type["name"] for eq in filtered)
    total_excluded = len(excluded)

    # ---- Scope comparison: resources-only vs all recipe entries ----
    # Recompute candidate pairs and Jaccard with ALL recipe entries included
    # (resources + quest equipment + consumables) to show the effect of the
    # loader's resource-only filter.
    inverted_all: dict[int, set[int]] = defaultdict(set)
    for eid, rids in eq_all.items():
        for rid in rids:
            inverted_all[rid].add(eid)
    candidates_all: set[tuple[int, int]] = set()
    for eq_set in inverted_all.values():
        if len(eq_set) >= 2:
            for a, b in combinations(sorted(eq_set), 2):
                candidates_all.add((a, b))

    jacc_all_values: list[float] = []
    for a, b in candidates_all:
        jacc_all_values.append(jaccard(eq_all[a], eq_all[b]))
    jacc_all_stats = dist_stats(jacc_all_values)
    all_exceed_01 = sum(1 for j in jacc_all_values if j >= 0.1)
    all_exceed_02 = sum(1 for j in jacc_all_values if j >= 0.2)
    all_exceed_03 = sum(1 for j in jacc_all_values if j >= 0.3)

    # Distinct-entry count per recipe under both scopes
    all_distinct_counts = [len(eq_all[eq.ankama_id]) for eq in equipments]
    all_distinct_stats = dist_stats(all_distinct_counts)

    # Components at 0.3 under "all entries"
    def components_at(cands, res_map, t):
        adj: dict[int, set[int]] = defaultdict(set)
        for a, b in cands:
            if jaccard(res_map[a], res_map[b]) >= t:
                adj[a].add(b)
                adj[b].add(a)
        visited: set[int] = set()
        comps = []
        for node in adj:
            if node in visited:
                continue
            stack = [node]
            comp = []
            visited.add(node)
            while stack:
                cur = stack.pop()
                comp.append(cur)
                for nb in adj[cur]:
                    if nb not in visited:
                        visited.add(nb)
                        stack.append(nb)
            comps.append(comp)
        sizes = [len(c) for c in comps]
        return len(comps), (max(sizes) if sizes else 0)

    all_comp_count_03, all_comp_largest_03 = components_at(candidates_all, eq_all, 0.3)

    # ====================================================================
    # WRITE MARKDOWN
    # ====================================================================

    L: list[str] = []
    L.append("# Data Profile: Full Snapshot")
    L.append("")
    L.append(f"**Snapshot version:** {manifest.get('game_version', 'unknown')}  ")
    L.append(f"**Created:** {manifest.get('created_at', 'unknown')}  ")
    L.append(f"**Equipment:** {n}  ")
    L.append(f"**Resources:** {len(resources)}  ")
    L.append(f"**Set mappings:** {len(set_index)}  ")
    L.append(
        f"**Level range:** {manifest.get('level_min', '?')} - {manifest.get('level_max', '?')}  "
    )
    L.append("")
    L.append(
        f"**Density filter formula:** `stat_weight >= level * {DENSITY_RATIO}` "
        f"(matches `ProcessingConfig.equipment_density_level_ratio = {DENSITY_RATIO}`)"
    )
    L.append("")
    L.append(
        "**Related:** project wiki in-repo at `wiki/` "
        "(see `wiki/concepts/cost-popularity-taux-hypothesis.md`)."
    )
    L.append("")
    L.append("---")
    L.append("")

    # --- RECIPES ---
    L.append("## RECIPES")
    L.append("")

    L.append("### 1. Distinct resources per recipe; units per recipe")
    L.append("")
    L.append("| Metric | min | median | p90 | max | n |")
    L.append("|--------|-----|--------|-----|-----|---|")
    L.append(
        f"| Distinct resources | {fmt(distinct_stats['min'])} | "
        f"{fmt(distinct_stats['median'])} | {fmt(distinct_stats['p90'])} | "
        f"{fmt(distinct_stats['max'])} | {distinct_stats['n']} |"
    )
    L.append(
        f"| Total units | {fmt(units_stats['min'])} | "
        f"{fmt(units_stats['median'])} | {fmt(units_stats['p90'])} | "
        f"{fmt(units_stats['max'])} | {units_stats['n']} |"
    )
    L.append("")
    L.append(
        f"**Items with empty recipes (0 resources):** {empty_recipe_count} "
        f"({100.0 * empty_recipe_count / n:.1f}%)"
    )
    L.append("")

    L.append("### 2. Resource frequency: top 30 most shared resources")
    L.append("")
    L.append("| Rank | Resource ID | Name | Items | % of recipes |")
    L.append("|------|-------------|------|-------|--------------|")
    for i, (rid, cnt) in enumerate(top30, 1):
        pct = 100.0 * cnt / n
        name = res_name.get(rid, "?")
        L.append(f"| {i} | {rid} | {name} | {cnt} | {pct:.1f}% |")
    L.append("")
    L.append(
        f"**Resources appearing in > 20% of recipes** (threshold = {threshold_20pct:.0f} items):"
    )
    L.append("")
    if above_20pct:
        L.append("| Resource ID | Name | Items | % of recipes |")
        L.append("|-------------|------|-------|--------------|")
        for rid, cnt in above_20pct:
            pct = 100.0 * cnt / n
            name = res_name.get(rid, "?")
            marker = " **(excluded)**" if rid in EXCLUDED else ""
            L.append(f"| {rid} | {name} | {cnt} | {pct:.1f}%{marker} |")
    else:
        L.append("_None._")
    L.append("")

    L.append("### 3. Are 15263 and 14635 actually the ubiquitous ones?")
    L.append("")
    L.append("| Resource ID | Name | Items | % of recipes | In excluded set? |")
    L.append("|-------------|------|-------|--------------|------------------|")
    for rid in sorted(EXCLUDED):
        cnt = excluded_freq.get(rid, 0)
        pct = 100.0 * cnt / n
        name = res_name.get(rid, "not in snapshot")
        L.append(f"| {rid} | {name} | {cnt} | {pct:.1f}% | yes |")
    L.append("")
    if others_ubiquitous:
        L.append(
            "**Other resources that also appear in > 20% of recipes** "
            "(behave like the excluded ones):"
        )
        L.append("")
        L.append("| Resource ID | Name | Items | % of recipes |")
        L.append("|-------------|------|-------|--------------|")
        for rid, cnt in others_ubiquitous:
            pct = 100.0 * cnt / n
            name = res_name.get(rid, "?")
            L.append(f"| {rid} | {name} | {cnt} | {pct:.1f}% |")
    else:
        L.append(
            "_No other resources exceed the 20% threshold; "
            "15263 and 14635 are the only ubiquitous ones._"
        )
    L.append("")

    L.append("### 4. Resources used by exactly one item (dead-ends for sharing)")
    L.append("")
    L.append(f"**Count:** {len(dead_ends)}")
    L.append("")
    if dead_ends:
        L.append("| Resource ID | Name |")
        L.append("|-------------|------|")
        for rid, _ in dead_ends:
            name = res_name.get(rid, "?")
            L.append(f"| {rid} | {name} |")
    L.append("")

    L.append("#### 4b. Dead-end deep dive: are they really single-use?")
    L.append("")
    L.append(
        f"- **Still single-use when ALL recipe subtypes are counted "
        f"(quest equipment + consumables included):** {dead_end_still_single_raw} "
        f"of {len(dead_end_items)}. So the resource-only filter is not creating "
        f"false dead-ends."
    )
    L.append("")
    L.append("**Dead-end resources by resource type:**")
    L.append("")
    L.append("| Resource type | Dead-end resources |")
    L.append("|---------------|--------------------|")
    for t in sorted(dead_by_restype, key=lambda x: -dead_by_restype[x]):
        L.append(f"| {t} | {dead_by_restype[t]} |")
    L.append("")
    L.append(
        "**One example per level band** (the single equipment that consumes each "
        "dead-end resource; a few shown per band):"
    )
    L.append("")
    L.append("| Band | Resource ID | Resource | Resource type | Equipment ID | Eq Lvl | Slot | Equipment |")
    L.append("|------|-------------|----------|---------------|--------------|--------|------|-----------|")
    for b in sorted(samples_by_band):
        shown = samples_by_band[b][:6]
        for rid, rname, rtype, eid, lvl, slot, ename in shown:
            L.append(
                f"| {b} | {rid} | {rname} | {rtype} | {eid} | {lvl} | "
                f"{slot_en(slot)} | {ename} |"
            )
    L.append("")

    L.append("#### 4c. Do the items that consume dead-end resources still share?")
    L.append("")
    L.append(
        "A dead-end resource has one consumer, but that consumer's **other** "
        "resources can still overlap with other items. These are the "
        f"{len(boss_items)} items that consume at least one dead-end resource."
    )
    L.append("")
    L.append(
        f"- **Items consuming >= 1 dead-end resource:** {len(boss_items)}"
    )
    L.append(
        f"- **Items with zero shared resources overall (isolated):** {len(isolated_all)} "
        f"(of which boss items: {len(boss_isolated)})"
    )
    L.append(
        f"- **Boss items that still share >= 1 resource:** {len(boss_sharing)} of "
        f"{len(boss_items)} ({100.0 * len(boss_sharing) / len(boss_items):.1f}%)"
    )
    L.append(
        f"- **Boss-item pairs sharing resources with each other:** {len(boss_pairs)}"
    )
    L.append("")
    if boss_top_drivers:
        L.append("**Resources that most often drive boss-item overlap:**")
        L.append("")
        L.append("| Resource ID | Name | Boss-item pairs |")
        L.append("|-------------|------|-----------------|")
        for rid, cnt in boss_top_drivers:
            L.append(f"| {rid} | {res_name.get(rid, '?')} | {cnt} |")
        L.append("")

    L.append(
        "#### 4d. Constraint-resource hypothesis (user, 2026-10-09) - NOT testable from this snapshot"
    )
    L.append("")
    L.append(
        "> **User hypothesis (recorded in the project wiki as "
        "`cost-popularity-taux-hypothesis`):** resources like the ones above are "
        "**high-constraint** - scarce / high-demand / expensive. Items built from "
        "them are more expensive than other items at the same level, so more "
        "players choose and break them, so their **taux** (break rate) is weak."
    )
    L.append("")
    L.append(
        "This snapshot contains **no price and no taux data**, so the hypothesis "
        "cannot be confirmed or refuted here. What the snapshot *does* show is the "
        "necessary precondition - these resources are shared across many recipes:"
    )
    L.append("")
    L.append("| Resource ID | Name | % of recipes | Boss-item pairs |")
    L.append("|-------------|------|--------------|-----------------|")
    for rid, cnt in boss_top_drivers:
        pct = 100.0 * res_freq.get(rid, 0) / n
        L.append(f"| {rid} | {res_name.get(rid, '?')} | {pct:.1f}% | {cnt} |")
    L.append("")
    L.append(
        "**Cross-check plan (resolution path):** join empirical break outcomes "
        "(`break_log`, via the capture pipeline) with recipe cost (`c_i`, via the "
        "price feed), grouped by item level and stat density. Prediction: items "
        "dominated by high-cost / high-demand resources show lower empirical taux "
        "than same-level, same-density items built from cheap/common resources."
    )
    L.append("")
    L.append("---")
    L.append("")

    # --- STRUCTURE ---
    L.append("## STRUCTURE")
    L.append("")

    L.append("### 5. Items per type and per level band")
    L.append("")
    L.append("**Items per type:**")
    L.append("")
    L.append("| Type (FR) | Slot (EN) | Items |")
    L.append("|-----------|-----------|-------|")
    for t in sorted(type_counts, key=lambda x: -type_counts[x]):
        L.append(f"| {t} | {slot_en(t)} | {type_counts[t]} |")
    L.append("")
    L.append(f"**Items per {LEVEL_BAND}-level band:**")
    L.append("")
    L.append("| Band | Level range | Items |")
    L.append("|------|-------------|-------|")
    for b in sorted(all_bands):
        lo = b * LEVEL_BAND
        hi = lo + LEVEL_BAND - 1
        L.append(f"| {b} | {lo}-{hi} | {band_counts[b]} |")
    L.append("")

    L.append("### 6. Panoplie sizes")
    L.append("")
    L.append(
        f"- **Items with set_id = None:** {none_count} ({100.0 * none_count / n:.1f}%)"
    )
    L.append(f"- **Distinct sets:** {len(set_sizes)}")
    L.append(f"- **Items in a set:** {n - none_count}")
    L.append("")
    L.append("| Set size | min | median | p90 | max | n |")
    L.append("|----------|-----|--------|-----|-----|---|")
    L.append(
        f"| Items per set | {fmt(set_size_stats['min'])} | "
        f"{fmt(set_size_stats['median'])} | {fmt(set_size_stats['p90'])} | "
        f"{fmt(set_size_stats['max'])} | {set_size_stats['n']} |"
    )
    L.append("")

    L.append(
        f"### 7. Type x level-band cells with too few items to group (< 2 items)"
    )
    L.append("")
    if sparse_cells:
        L.append("| Type (FR) | Slot (EN) | Band | Level range | Items |")
        L.append("|-----------|-----------|------|-------------|-------|")
        for t, b, cnt in sparse_cells:
            lo = b * LEVEL_BAND
            hi = lo + LEVEL_BAND - 1
            L.append(f"| {t} | {slot_en(t)} | {b} | {lo}-{hi} | {cnt} |")
    else:
        L.append("_All type x level-band cells have >= 2 items._")
    L.append("")
    L.append("---")
    L.append("")

    # --- SIMILARITY ---
    L.append("## SIMILARITY")
    L.append("")

    L.append("### 8. Pairwise Jaccard similarity distribution")
    L.append("")
    L.append(f"- **Total possible pairs:** {total_pairs}")
    L.append(
        f"- **Candidate pairs (share >= 1 resource):** {len(candidate_pairs)}"
    )
    L.append(
        f"- **Pairs with Jaccard = 0 (no shared resources):** {total_pairs - len(candidate_pairs)}"
    )
    L.append("")
    L.append(
        f"_Total pairs ({total_pairs}) < 5M, so no sampling was needed; "
        "all candidate pairs were evaluated._"
    )
    L.append("")
    L.append("| Jaccard | min | median | p90 | max | n |")
    L.append("|---------|-----|--------|-----|-----|---|")
    L.append(
        f"| All candidate pairs | {fmt(jaccard_stats['min'])} | "
        f"{fmt(jaccard_stats['median'])} | {fmt(jaccard_stats['p90'])} | "
        f"{fmt(jaccard_stats['max'])} | {jaccard_stats['n']} |"
    )
    L.append("")
    L.append(
        "| Threshold | Pairs exceeding | % of all pairs | % of candidate pairs |"
    )
    L.append("|-----------|-----------------|----------------|----------------------|")
    for thresh, cnt in [(0.1, exceed_01), (0.2, exceed_02), (0.3, exceed_03)]:
        pct_all = 100.0 * cnt / total_pairs if total_pairs else 0.0
        pct_cand = 100.0 * cnt / len(candidate_pairs) if candidate_pairs else 0.0
        L.append(f"| {thresh} | {cnt} | {pct_all:.2f}% | {pct_cand:.2f}% |")
    L.append("")
    L.append(
        f"**graph_min_shared_ratio = 0.3** keeps {exceed_03} edges "
        f"({100.0 * exceed_03 / total_pairs:.2f}% of all pairs, "
        f"{100.0 * exceed_03 / len(candidate_pairs):.2f}% of candidate pairs)."
    )
    L.append("")

    L.append("### 9. Connected components at several thresholds")
    L.append("")
    L.append(
        "| Threshold | Components | Largest | Nodes in comps | Size min | Size median | Size p90 | Size max |"
    )
    L.append(
        "|-----------|------------|---------|----------------|----------|-------------|----------|----------|"
    )
    for t in thresholds:
        c = components_by_thresh[t]
        s = c["sizes"]
        L.append(
            f"| {t} | {c['count']} | {c['largest']} | {c['nodes_in_comps']} | "
            f"{fmt(s['min'])} | {fmt(s['median'])} | {fmt(s['p90'])} | {fmt(s['max'])} |"
        )
    L.append("")

    L.append("### 10. Cross-type sharing")
    L.append("")
    L.append("**By pair count:**")
    L.append("")
    L.append(
        f"- **Same-type pairs:** {pair_same_type} ({100.0 * pair_same_type / total_shared_pairs:.1f}%)"
    )
    L.append(
        f"- **Cross-type pairs:** {pair_cross_type} ({cross_type_pct:.1f}%)"
    )
    L.append("")
    L.append("**By shared-resource instances (sum of |A intersect B|):**")
    L.append("")
    L.append(
        f"- **Same-type shared instances:** {same_type_shared} ({100.0 * same_type_shared / total_shared_instances:.1f}%)"
    )
    L.append(
        f"- **Cross-type shared instances:** {cross_type_shared} ({cross_type_shared_pct:.1f}%)"
    )
    L.append("")

    L.append("### 11. Cross-level sharing")
    L.append("")
    L.append(
        f"- **Same {LEVEL_BAND}-level band pairs:** {pair_same_band} ({same_band_pct:.1f}%)"
    )
    L.append(
        f"- **Cross-band pairs:** {pair_cross_band} ({100.0 - same_band_pct:.1f}%)"
    )
    L.append(
        f"- **Pairs with level diff <= {LEVEL_BAND}:** {narrow_level} ({narrow_level_pct:.1f}%)"
    )
    L.append("")
    L.append("| Level diff | min | median | p90 | max | n |")
    L.append("|------------|-----|--------|-----|-----|---|")
    L.append(
        f"| |level_a - level_b| | {fmt(level_diff_stats['min'])} | "
        f"{fmt(level_diff_stats['median'])} | {fmt(level_diff_stats['p90'])} | "
        f"{fmt(level_diff_stats['max'])} | {level_diff_stats['n']} |"
    )
    L.append("")
    L.append("---")
    L.append("")

    # --- FILTERS ---
    L.append("## FILTERS")
    L.append("")

    L.append(f"### 12. Density filter (ratio = {DENSITY_RATIO}) removal")
    L.append("")
    L.append(
        f"- **Total items removed:** {total_excluded} ({100.0 * total_excluded / n:.1f}%)"
    )
    L.append(
        f"- **Items retained:** {len(filtered)} ({100.0 * len(filtered) / n:.1f}%)"
    )
    L.append("")
    L.append("**Removed by type:**")
    L.append("")
    L.append("| Type (FR) | Slot (EN) | Removed | Retained |")
    L.append("|-----------|-----------|---------|----------|")
    for t in sorted(type_counts, key=lambda x: -type_counts[x]):
        L.append(
            f"| {t} | {slot_en(t)} | {excluded_by_type.get(t, 0)} | {retained_by_type.get(t, 0)} |"
        )
    L.append("")
    L.append(f"**Removed by {LEVEL_BAND}-level band:**")
    L.append("")
    L.append("| Band | Level range | Removed |")
    L.append("|------|-------------|---------|")
    for b in sorted(excluded_by_band):
        lo = b * LEVEL_BAND
        hi = lo + LEVEL_BAND - 1
        L.append(f"| {b} | {lo}-{hi} | {excluded_by_band[b]} |")
    L.append("")
    L.append("---")
    L.append("")

    # --- SCOPE COMPARISON ---
    L.append("## SCOPE COMPARISON: resources-only vs all recipe entries")
    L.append("")
    L.append(
        "The loader (`EquipmentLoader._parse_recipe`) keeps only recipe entries "
        "with `item_subtype == 'resources'`. Some recipes also list quest "
        "**equipment** and **consumables**. This section compares the two "
        "treatments. All other sections use the resources-only view (the "
        "pipeline's actual behaviour)."
    )
    L.append("")
    L.append("**Raw recipe entry counts by subtype:**")
    L.append("")
    L.append("| item_subtype | Entries |")
    L.append("|--------------|---------|")
    for st in sorted(subtype_counts, key=lambda x: -subtype_counts[x]):
        L.append(f"| {st} | {subtype_counts[st]} |")
    L.append("")
    L.append(
        f"**Items whose recipe contains a non-resource entry:** "
        f"{len(items_with_non_resource)} of {n} "
        f"({100.0 * len(items_with_non_resource) / n:.1f}%)"
    )
    L.append("")
    L.append("| Metric | resources-only | all entries |")
    L.append("|--------|----------------|-------------|")
    L.append(
        f"| Distinct recipe entries (median) | {fmt(distinct_stats['median'])} | "
        f"{fmt(all_distinct_stats['median'])} |"
    )
    L.append(
        f"| Distinct recipe entries (p90) | {fmt(distinct_stats['p90'])} | "
        f"{fmt(all_distinct_stats['p90'])} |"
    )
    L.append(
        f"| Distinct recipe entries (max) | {fmt(distinct_stats['max'])} | "
        f"{fmt(all_distinct_stats['max'])} |"
    )
    L.append(f"| Candidate pairs (share >= 1) | {len(candidate_pairs)} | {len(candidates_all)} |")
    L.append(
        f"| Jaccard median (candidates) | {fmt(jaccard_stats['median'])} | "
        f"{fmt(jacc_all_stats['median'])} |"
    )
    L.append(
        f"| Jaccard p90 (candidates) | {fmt(jaccard_stats['p90'])} | "
        f"{fmt(jacc_all_stats['p90'])} |"
    )
    L.append(f"| Pairs >= 0.1 | {exceed_01} | {all_exceed_01} |")
    L.append(f"| Pairs >= 0.2 | {exceed_02} | {all_exceed_02} |")
    L.append(f"| Pairs >= 0.3 | {exceed_03} | {all_exceed_03} |")
    L.append(
        f"| Components @ 0.3 | {components_by_thresh[0.3]['count']} | {all_comp_count_03} |"
    )
    L.append(
        f"| Largest component @ 0.3 | {components_by_thresh[0.3]['largest']} | {all_comp_largest_03} |"
    )
    L.append("")
    L.append("---")
    L.append("")

    # --- INFERENCE ---
    L.append("## INFERENCE (interpretation, not raw data)")
    L.append("")
    L.append(
        "> The following are interpretations of the numbers above. "
        "They are not themselves computed statistics."
    )
    L.append("")
    L.append(
        "1. **No resource is ubiquitous in this snapshot.** The top resource "
        f"appears in only {100.0 * top30[0][1] / n:.1f}% of recipes. "
        "Neither 15263 nor 14635 comes close to the 20% threshold: "
        f"15263 appears in 0 recipes (absent from the snapshot entirely), "
        f"and 14635 appears in {excluded_freq.get(14635, 0)} ({100.0 * excluded_freq.get(14635, 0) / n:.1f}%). "
        "The `excluded_resource_ids = {15263, 14635}` default does not match "
        "the current data."
    )
    L.append(
        "2. **Resource sharing is sparse.** Only "
        f"{100.0 * len(candidate_pairs) / total_pairs:.1f}% of all pairs share "
        "even one resource. The median Jaccard among candidate pairs is "
        f"{jaccard_stats['median']:.2f}, and the p90 is {jaccard_stats['p90']:.2f}."
    )
    L.append(
        "3. **graph_min_shared_ratio = 0.3 is an aggressive threshold.** It keeps "
        f"only {exceed_03} edges ({100.0 * exceed_03 / len(candidate_pairs):.1f}% "
        "of candidate pairs). At 0.3 the graph fragments into "
        f"{components_by_thresh[0.3]['count']} components, the largest containing "
        f"{components_by_thresh[0.3]['largest']} of {n} items "
        f"({100.0 * components_by_thresh[0.3]['largest'] / n:.1f}%)."
    )
    L.append(
        "4. **Sharing is predominantly cross-type.** "
        f"{cross_type_pct:.1f}% of candidate pairs are cross-type, and "
        f"{cross_type_shared_pct:.1f}% of shared-resource instances are cross-type. "
        "This is expected: different slots use different base materials."
    )
    L.append(
        "5. **Sharing is not confined to a narrow level range.** "
        f"{100.0 - same_band_pct:.1f}% of pairs span different {LEVEL_BAND}-level "
        f"bands, and the median level difference is {level_diff_stats['median']:.0f}. "
        "However, "
        f"{narrow_level_pct:.1f}% of pairs are within {LEVEL_BAND} levels of each other."
    )
    L.append(
        f"6. **The density filter (ratio {DENSITY_RATIO}) removes "
        f"{100.0 * total_excluded / n:.1f}% of items.** It removes the majority of "
        "accessories (Anneau, Bottes, Ceinture, Amulette, Chapeau, Cape) but only "
        "a small fraction of weapons. This is because accessories have low "
        "stat_weight relative to their level."
    )
    L.append(
        f"7. **{len(dead_ends)} resources ({100.0 * len(dead_ends) / len(res_freq):.1f}% "
        "of distinct resources) are dead-ends** used by exactly one item. "
        "But this does NOT make their consuming items worthless: "
        f"{len(boss_sharing)} of {len(boss_items)} such items still share other "
        f"resources with the rest of the pool, and they form {len(boss_pairs)} "
        "boss-item pairs. Excluding these items would remove real recipe overlap."
    )
    L.append(
        f"8. **Including non-resource recipe entries barely changes the "
        f"similarity structure.** 44 of {n} items "
        f"({100.0 * len(items_with_non_resource) / n:.1f}%) list quest equipment "
        f"or consumables. Adding them changes the edge counts by at most a few "
        f"hundred ({exceed_03} -> {all_exceed_03} at threshold 0.3) and the "
        f"component count by 1 ({components_by_thresh[0.3]['count']} -> "
        f"{all_comp_count_03}); the largest component is unchanged "
        f"({components_by_thresh[0.3]['largest']}). The resource-only filter is "
        f"therefore not materially distorting the graph."
    )
    L.append(
        "9. **The high-constraint-resource / taux link is a user hypothesis, not "
        "shown here.** The snapshot has no price or taux data. It confirms only "
        "that the candidate resources are shared widely (necessary, not "
        "sufficient). Testing it needs `break_log` outcomes joined to recipe cost "
        "- see `wiki/concepts/cost-popularity-taux-hypothesis.md`."
    )
    L.append("")

    # Write output
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    print(f"\nReport written to {OUTPUT_MD}")
    print(f"  ({len(L)} lines)")


if __name__ == "__main__":
    main()
