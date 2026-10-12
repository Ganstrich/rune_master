#!/usr/bin/env python3
"""Descriptive profile of the frozen equipment snapshot.

READ-ONLY analysis. Loads the frozen snapshot via data.snapshot.load_snapshot,
describes what the data contains (recipes, resources, equipment, sets,
statistics, sharing structure), and writes plans/data-profile.md.

No hypotheses, no thresholds borrowed from pipeline config, no exclusion
recommendations. Every number comes from the script's output.
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
from processing.valuation.density import RUNE_DENSITY, resolve_stat_name

SNAPSHOT_DIR = Path(__file__).parent.parent / "data" / "snapshots" / "3.7.7.6"
OUTPUT_MD = Path(__file__).parent.parent / "plans" / "data-profile.md"

# French type name -> English slot name (for readability)
SLOT_EN = {
    "Anneau": "ring", "Bottes": "boots", "Chapeau": "hat", "Ceinture": "belt",
    "Amulette": "amulet", "Cape": "cloak", "Bouclier": "shield", "Épée": "sword",
    "Marteau": "hammer", "Bâton": "staff", "Baguette": "wand", "Dague": "dagger",
    "Arc": "bow", "Hache": "axe", "Pelle": "shovel", "Lance": "lance", "Faux": "scythe",
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


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def break_density(effects: list[dict]) -> float:
    """Compute total rune density from raw effect dicts (sum of value * density)."""
    total = 0.0
    for eff in effects or []:
        raw_name = eff.get("type", {}).get("name", "")
        try:
            stat_name = resolve_stat_name(raw_name)
        except KeyError:
            continue
        v_min = float(eff.get("int_minimum", 0) or 0)
        v_max = float(eff.get("int_maximum", 0) or 0)
        value = max((v_min + v_max) / 2, 0.0)
        total += value * RUNE_DENSITY[stat_name]
    return total


def main() -> None:
    print(f"Loading snapshot from {SNAPSHOT_DIR} ...")
    equipments, resources, set_index = load_snapshot(SNAPSHOT_DIR)
    manifest = load_manifest(SNAPSHOT_DIR)

    n = len(equipments)
    print(f"  Equipment: {n}")
    print(f"  Resources: {len(resources)}")
    print(f"  Set mappings: {len(set_index)}")

    # ---- Direct sqlite reads for raw recipe entries and effects ----
    import sqlite3
    conn = sqlite3.connect(str(SNAPSHOT_DIR / "snapshot.db"))
    conn.row_factory = sqlite3.Row
    raw_equipment = {}
    for row in conn.execute("SELECT data FROM equipment"):
        raw = json.loads(row["data"])
        raw_equipment[int(raw["ankama_id"])] = raw
    raw_resources = {
        int(json.loads(r["data"])["ankama_id"]): json.loads(r["data"])
        for r in conn.execute("SELECT data FROM resources")
    }
    conn.close()

    # Resource id -> name, type, level
    res_name = {rid: r["name"] for rid, r in raw_resources.items()}
    res_type = {rid: r["type"]["name"] for rid, r in raw_resources.items()}

    # ====================================================================
    # LOAD AND INDEX
    # ====================================================================

    # Resources-only view (matches loader scope)
    eq_recipes: dict[int, dict[int, int]] = {}
    for eid, raw in raw_equipment.items():
        rec = {}
        for item in raw.get("recipe", []):
            if item.get("item_subtype") == "resources":
                rid = int(item["item_ankama_id"])
                rec[rid] = rec.get(rid, 0) + int(item["quantity"])
        eq_recipes[eid] = rec

    # All-entries view (resources + equipment + consumables)
    eq_all_entries: dict[int, dict[int, int]] = {}
    subtype_counts: Counter = Counter()
    for eid, raw in raw_equipment.items():
        rec = {}
        for item in raw.get("recipe", []):
            st = item.get("item_subtype", "MISSING")
            subtype_counts[st] += 1
            rid = int(item["item_ankama_id"])
            rec[rid] = rec.get(rid, 0) + int(item["quantity"])
        eq_all_entries[eid] = rec

    # Inverted index: resource_id -> set of equipment_ids (resources-only)
    inverted: dict[int, set[int]] = defaultdict(set)
    for eid, rec in eq_recipes.items():
        for rid in rec:
            inverted[rid].add(eid)

    # Inverted index (all entries)
    inverted_all: dict[int, set[int]] = defaultdict(set)
    for eid, rec in eq_all_entries.items():
        for rid in rec:
            inverted_all[rid].add(eid)

    # Equipment lookups
    eq_level = {eq.ankama_id: eq.level for eq in equipments}
    eq_type = {eq.ankama_id: eq.type["name"] for eq in equipments}
    eq_set_id = {eq.ankama_id: eq.set_id for eq in equipments}
    eq_name = {eq.ankama_id: eq.name for eq in equipments}

    # Break density per item (from raw effects)
    eq_break_density = {
        eid: break_density(raw.get("effects", []))
        for eid, raw in raw_equipment.items()
    }

    # ====================================================================
    # 1. RESOURCES: breadth distribution
    # ====================================================================
    breadth = {rid: len(eq_set) for rid, eq_set in inverted.items()}
    sorted_breadth = sorted(breadth.items(), key=lambda x: (-x[1], x[0]))
    breadth_values = list(breadth.values())
    breadth_stats = dist_stats(breadth_values)

    # ====================================================================
    # 2. RESOURCES: depth (units per item)
    # ====================================================================
    depth_per_item: dict[int, list[int]] = defaultdict(list)
    for eid, rec in eq_recipes.items():
        for rid, qty in rec.items():
            depth_per_item[rid].append(qty)

    avg_depth = {}
    max_depth = {}
    for rid, qtys in depth_per_item.items():
        avg_depth[rid] = sum(qtys) / len(qtys)
        max_depth[rid] = max(qtys)

    # ====================================================================
    # 3. RESOURCES: breadth x depth classification
    # ====================================================================
    broad_threshold = 50
    classes: dict[str, list] = defaultdict(list)
    for rid, br in sorted_breadth:
        if br < 2:
            continue
        ad = avg_depth.get(rid, 0)
        md = max_depth.get(rid, 0)
        if br >= broad_threshold and ad > 100:
            classes["broad_heavy"].append((rid, br, ad, md))
        elif br >= broad_threshold and md <= 2:
            classes["broad_trivial"].append((rid, br, ad, md))
        elif br >= broad_threshold:
            classes["broad_medium"].append((rid, br, ad, md))
        elif br >= 10:
            classes["narrow_any"].append((rid, br, ad, md))
        else:
            classes["rare_any"].append((rid, br, ad, md))

    # Candidate pairs contributed by each class
    class_pairs: dict[str, set] = defaultdict(set)
    for rid, br in sorted_breadth:
        item_set = inverted[rid]
        if len(item_set) < 2:
            continue
        ad = avg_depth.get(rid, 0)
        md = max_depth.get(rid, 0)
        if br >= broad_threshold and ad > 100:
            cls = "broad_heavy"
        elif br >= broad_threshold and md <= 2:
            cls = "broad_trivial"
        elif br >= broad_threshold:
            cls = "broad_medium"
        elif br >= 10:
            cls = "narrow_any"
        else:
            cls = "rare_any"
        for a, b in combinations(sorted(item_set), 2):
            class_pairs[cls].add((a, b))

    # Total candidate pairs
    total_candidate_pairs: set = set()
    for eq_set in inverted.values():
        if len(eq_set) >= 2:
            for a, b in combinations(sorted(eq_set), 2):
                total_candidate_pairs.add((a, b))

    # ====================================================================
    # 4. RESOURCES: dead-ends (used by exactly 1 item)
    # ====================================================================
    dead_ends = [(rid, br) for rid, br in sorted_breadth if br == 1]

    # Cross-check under all-entries scope
    raw_breadth = {rid: len(eq_set) for rid, eq_set in inverted_all.items()}
    dead_still_single = sum(
        1 for rid, _ in dead_ends if raw_breadth.get(rid, 0) <= 1
    )

    # Dead-ends by resource type
    dead_by_type = Counter(res_type.get(rid, "unknown") for rid, _ in dead_ends)

    # Items consuming dead-end resources
    dead_single = {rid: next(iter(inverted[rid])) for rid, _ in dead_ends}
    boss_items = set(dead_single.values())

    # Do boss items still share with the rest of the pool?
    boss_sharing = set()
    for eid in boss_items:
        for rid in eq_recipes[eid]:
            others = inverted[rid] - {eid}
            if others:
                boss_sharing.add(eid)
                break
    boss_isolated = boss_items - boss_sharing

    # Boss-item pairs sharing resources
    boss_pairs = []
    for a, b in combinations(sorted(boss_items), 2):
        shared = set(eq_recipes[a]) & set(eq_recipes[b])
        if shared:
            boss_pairs.append((a, b, len(shared)))

    # Which resources drive boss-item overlap
    boss_drivers: Counter = Counter()
    for a, b, _ in boss_pairs:
        for rid in set(eq_recipes[a]) & set(eq_recipes[b]):
            boss_drivers[rid] += 1

    # ====================================================================
    # 5. EQUIPMENT: type and level distribution
    # ====================================================================
    type_counts = Counter(eq_type.values())
    band_counts = Counter(lvl // 20 for lvl in eq_level.values())

    # ====================================================================
    # 6. EQUIPMENT: recipe size and total units
    # ====================================================================
    distinct_per_recipe = [len(rec) for rec in eq_recipes.values()]
    total_units_per_recipe = [sum(rec.values()) for rec in eq_recipes.values()]
    empty_recipes = [eid for eid, rec in eq_recipes.items() if len(rec) == 0]
    distinct_stats = dist_stats(distinct_per_recipe)
    units_stats = dist_stats(total_units_per_recipe)

    # ====================================================================
    # 7. EQUIPMENT: break density distribution
    # ====================================================================
    bd_values = list(eq_break_density.values())
    bd_stats = dist_stats(bd_values)
    bd_by_band: dict[int, list] = defaultdict(list)
    for eid, bd in eq_break_density.items():
        bd_by_band[eq_level[eid] // 20].append(bd)
    bd_by_band_stats = {
        b: dist_stats(vals) for b, vals in sorted(bd_by_band.items())
    }

    # ====================================================================
    # 8. SETS: panoplie structure
    # ====================================================================
    set_members: dict[int, list[int]] = defaultdict(list)
    setless = []
    for eid, sid in eq_set_id.items():
        if sid is None:
            setless.append(eid)
        else:
            set_members[sid].append(eid)
    set_sizes = [len(members) for members in set_members.values()]
    set_size_stats = dist_stats(set_sizes)

    # ====================================================================
    # 9. SIMILARITY: pairwise Jaccard
    # ====================================================================
    jaccard_values = []
    for a, b in total_candidate_pairs:
        jaccard_values.append(jaccard(set(eq_recipes[a]), set(eq_recipes[b])))
    jaccard_stats = dist_stats(jaccard_values)

    # Jaccard at several thresholds
    thresholds = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]
    jaccard_thresholds = {}
    for t in thresholds:
        cnt = sum(1 for j in jaccard_values if j >= t)
        jaccard_thresholds[t] = cnt

    # Connected components at several thresholds
    components_by_thresh = {}
    for t in thresholds:
        adj: dict[int, set[int]] = defaultdict(set)
        for a, b in total_candidate_pairs:
            if jaccard(set(eq_recipes[a]), set(eq_recipes[b])) >= t:
                adj[a].add(b)
                adj[b].add(a)
        visited = set()
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

    # ====================================================================
    # 10. SIMILARITY: cross-type and cross-level
    # ====================================================================
    pair_same_type = 0
    pair_cross_type = 0
    pair_same_band = 0
    pair_cross_band = 0
    level_diffs = []
    for a, b in total_candidate_pairs:
        if eq_type[a] == eq_type[b]:
            pair_same_type += 1
        else:
            pair_cross_type += 1
        if eq_level[a] // 20 == eq_level[b] // 20:
            pair_same_band += 1
        else:
            pair_cross_band += 1
        level_diffs.append(abs(eq_level[a] - eq_level[b]))
    level_diff_stats = dist_stats(level_diffs)

    # ====================================================================
    # 11. SCOPE NOTE: why only resources-only
    # ====================================================================
    items_with_non_resource = {
        eid for eid in eq_all_entries
        if eq_all_entries[eid] != eq_recipes.get(eid, {})
    }

    # ====================================================================
    # WRITE MARKDOWN
    # ====================================================================
    L: list[str] = []
    L.append("# Data Profile: Full Snapshot")
    L.append("")
    L.append(f"**Snapshot version:** {manifest.get('game_version', 'unknown')}  ")
    L.append(f"**Created:** {manifest.get('created_at', 'unknown')}  ")
    L.append(f"**Equipment:** {n}  ")
    L.append(f"**Resources:** {len(raw_resources)}  ")
    L.append(f"**Set mappings:** {len(set_index)}  ")
    L.append(f"**Level range:** {manifest.get('level_min', '?')} - {manifest.get('level_max', '?')}  ")
    L.append("")
    L.append("---")
    L.append("")

    # --- RESOURCES ---
    L.append("## RESOURCES")
    L.append("")

    L.append("### 1. Resource breadth: how many items use each resource")
    L.append("")
    L.append("| Metric | min | median | p90 | max | n |")
    L.append("|--------|-----|--------|-----|-----|---|")
    L.append(
        f"| Items per resource | {fmt(breadth_stats['min'])} | "
        f"{fmt(breadth_stats['median'])} | {fmt(breadth_stats['p90'])} | "
        f"{fmt(breadth_stats['max'])} | {breadth_stats['n']} |"
    )
    L.append("")
    L.append("**Top 30 most-shared resources:**")
    L.append("")
    L.append("| Rank | Resource ID | Name | Type | Items | Avg units/item | Max units/item |")
    L.append("|------|-------------|------|------|-------|----------------|-----------------|")
    for i, (rid, cnt) in enumerate(sorted_breadth[:30], 1):
        L.append(
            f"| {i} | {rid} | {res_name.get(rid, '?')} | {res_type.get(rid, '?')} | "
            f"{cnt} | {fmt(avg_depth.get(rid, 0))} | {fmt(max_depth.get(rid, 0))} |"
        )
    L.append("")

    L.append("### 2. Resource depth: units per item")
    L.append("")
    avg_depth_values = [avg_depth.get(rid, 0) for rid, _ in sorted_breadth]
    max_depth_values = [max_depth.get(rid, 0) for rid, _ in sorted_breadth]
    ad_stats = dist_stats(avg_depth_values)
    md_stats = dist_stats(max_depth_values)
    L.append("| Metric | min | median | p90 | max | n |")
    L.append("|--------|-----|--------|-----|-----|---|")
    L.append(
        f"| Avg units per item | {fmt(ad_stats['min'])} | {fmt(ad_stats['median'])} | "
        f"{fmt(ad_stats['p90'])} | {fmt(ad_stats['max'])} | {ad_stats['n']} |"
    )
    L.append(
        f"| Max units per item | {fmt(md_stats['min'])} | {fmt(md_stats['median'])} | "
        f"{fmt(md_stats['p90'])} | {fmt(md_stats['max'])} | {md_stats['n']} |"
    )
    L.append("")

    L.append("### 3. Breadth x depth classification")
    L.append("")
    L.append(
        f"Resources used by >= 2 items, classified by breadth "
        f"(>= {broad_threshold} items = broad) and depth "
        f"(avg > 100 units = heavy, max <= 2 units = trivial):"
    )
    L.append("")
    L.append("| Class | Resources | Candidate pairs | % of all pairs |")
    L.append("|-------|-----------|-----------------|----------------|")
    for cls in ["broad_heavy", "broad_medium", "broad_trivial", "narrow_any", "rare_any"]:
        cnt = len(classes.get(cls, []))
        pairs = len(class_pairs.get(cls, set()))
        pct = 100.0 * pairs / len(total_candidate_pairs) if total_candidate_pairs else 0
        L.append(f"| {cls} | {cnt} | {pairs} | {pct:.1f}% |")
    L.append("")

    for cls, label in [
        ("broad_heavy", "Broad + heavy (>= 50 items, avg > 100 units)"),
        ("broad_medium", "Broad + medium (>= 50 items, 3-100 units)"),
        ("broad_trivial", "Broad + trivial (>= 50 items, max <= 2 units)"),
    ]:
        items = classes.get(cls, [])
        if not items:
            continue
        L.append(f"**{label}:**")
        L.append("")
        L.append("| Resource ID | Name | Type | Items | Avg units | Max units |")
        L.append("|-------------|------|------|-------|-----------|-----------|")
        for rid, br, ad, md in sorted(items, key=lambda x: -x[1]):
            L.append(
                f"| {rid} | {res_name.get(rid, '?')} | {res_type.get(rid, '?')} | "
                f"{br} | {fmt(ad)} | {fmt(md)} |"
            )
        L.append("")

    L.append("### 4. Resources used by exactly one item (dead-ends)")
    L.append("")
    L.append(f"**Count:** {len(dead_ends)}")
    L.append("")
    L.append(f"- **Still single-use under all-entries scope:** {dead_still_single} of {len(dead_ends)}")
    L.append("")

    L.append("**Dead-end resources by type:**")
    L.append("")
    L.append("| Resource type | Dead-end resources |")
    L.append("|---------------|--------------------|")
    for t in sorted(dead_by_type, key=lambda x: -dead_by_type[x]):
        L.append(f"| {t} | {dead_by_type[t]} |")
    L.append("")

    L.append("#### 4a. Do items consuming dead-end resources still share?")
    L.append("")
    L.append(f"- **Items consuming >= 1 dead-end resource:** {len(boss_items)}")
    L.append(f"- **Items with zero shared resources overall (isolated):** {len(boss_isolated)}")
    L.append(
        f"- **Items that still share >= 1 resource with the pool:** "
        f"{len(boss_sharing)} of {len(boss_items)} "
        f"({100.0 * len(boss_sharing) / len(boss_items):.1f}%)"
    )
    L.append(f"- **Pairs of such items sharing resources with each other:** {len(boss_pairs)}")
    L.append("")
    if boss_drivers:
        L.append("**Resources that most often drive overlap among these items:**")
        L.append("")
        L.append("| Resource ID | Name | Pairs bridged |")
        L.append("|-------------|------|---------------|")
        for rid, cnt in boss_drivers.most_common(10):
            L.append(f"| {rid} | {res_name.get(rid, '?')} | {cnt} |")
        L.append("")

    L.append("---")
    L.append("")

    # --- EQUIPMENT ---
    L.append("## EQUIPMENT")
    L.append("")

    L.append("### 5. Items per type")
    L.append("")
    L.append("| Type (FR) | Slot (EN) | Items | % of pool |")
    L.append("|-----------|-----------|-------|-----------|")
    for t in sorted(type_counts, key=lambda x: -type_counts[x]):
        L.append(f"| {t} | {slot_en(t)} | {type_counts[t]} | {100.0 * type_counts[t] / n:.1f}% |")
    L.append("")

    L.append("### 6. Items per 20-level band")
    L.append("")
    L.append("| Band | Level range | Items |")
    L.append("|------|-------------|-------|")
    for b in sorted(band_counts):
        lo = b * 20
        hi = lo + 19
        L.append(f"| {b} | {lo}-{hi} | {band_counts[b]} |")
    L.append("")

    L.append("### 7. Recipe size: distinct resources and total units")
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
    L.append(f"**Items with empty recipes (0 resources):** {len(empty_recipes)}")
    L.append("")

    L.append("### 8. Break density per item")
    L.append("")
    L.append("| Metric | min | median | p90 | max | n |")
    L.append("|--------|-----|--------|-----|-----|---|")
    L.append(
        f"| Break density | {fmt(bd_stats['min'])} | {fmt(bd_stats['median'])} | "
        f"{fmt(bd_stats['p90'])} | {fmt(bd_stats['max'])} | {bd_stats['n']} |"
    )
    L.append("")
    L.append("**Break density by 20-level band:**")
    L.append("")
    L.append("| Band | Level range | min | median | p90 | max | n |")
    L.append("|------|-------------|-----|--------|-----|-----|---|")
    for b in sorted(bd_by_band_stats):
        s = bd_by_band_stats[b]
        lo = b * 20
        hi = lo + 19
        L.append(
            f"| {b} | {lo}-{hi} | {fmt(s['min'])} | {fmt(s['median'])} | "
            f"{fmt(s['p90'])} | {fmt(s['max'])} | {s['n']} |"
        )
    L.append("")

    L.append("---")
    L.append("")

    # --- SETS ---
    L.append("## SETS")
    L.append("")
    L.append(f"- **Items with set_id = None:** {len(setless)} ({100.0 * len(setless) / n:.1f}%)")
    L.append(f"- **Distinct sets:** {len(set_members)}")
    L.append(f"- **Items in a set:** {n - len(setless)}")
    L.append("")
    L.append("| Set size | min | median | p90 | max | n |")
    L.append("|----------|-----|--------|-----|-----|---|")
    L.append(
        f"| Items per set | {fmt(set_size_stats['min'])} | {fmt(set_size_stats['median'])} | "
        f"{fmt(set_size_stats['p90'])} | {fmt(set_size_stats['max'])} | {set_size_stats['n']} |"
    )
    L.append("")

    L.append("---")
    L.append("")

    # --- SIMILARITY ---
    L.append("## SIMILARITY")
    L.append("")

    L.append("### 9. Pairwise Jaccard similarity")
    L.append("")
    total_pairs = n * (n - 1) // 2
    L.append(f"- **Total possible pairs:** {total_pairs}")
    L.append(f"- **Candidate pairs (share >= 1 resource):** {len(total_candidate_pairs)}")
    L.append(f"- **Pairs with Jaccard = 0 (no shared resources):** {total_pairs - len(total_candidate_pairs)}")
    L.append("")
    L.append("| Jaccard | min | median | p90 | max | n |")
    L.append("|---------|-----|--------|-----|-----|---|")
    L.append(
        f"| All candidate pairs | {fmt(jaccard_stats['min'])} | "
        f"{fmt(jaccard_stats['median'])} | {fmt(jaccard_stats['p90'])} | "
        f"{fmt(jaccard_stats['max'])} | {jaccard_stats['n']} |"
    )
    L.append("")
    L.append("| Threshold | Pairs >= | % of all pairs | % of candidate pairs |")
    L.append("|-----------|----------|----------------|----------------------|")
    for t in thresholds:
        cnt = jaccard_thresholds[t]
        pct_all = 100.0 * cnt / total_pairs if total_pairs else 0
        pct_cand = 100.0 * cnt / len(total_candidate_pairs) if total_candidate_pairs else 0
        L.append(f"| {t} | {cnt} | {pct_all:.2f}% | {pct_cand:.2f}% |")
    L.append("")

    L.append("### 10. Connected components at several thresholds")
    L.append("")
    L.append("| Threshold | Components | Largest | Nodes in comps | Size min | Size median | Size p90 | Size max |")
    L.append("|-----------|------------|---------|----------------|----------|-------------|----------|----------|")
    for t in thresholds:
        c = components_by_thresh[t]
        s = c["sizes"]
        L.append(
            f"| {t} | {c['count']} | {c['largest']} | {c['nodes_in_comps']} | "
            f"{fmt(s['min'])} | {fmt(s['median'])} | {fmt(s['p90'])} | {fmt(s['max'])} |"
        )
    L.append("")

    L.append("### 11. Cross-type sharing")
    L.append("")
    total_shared = pair_same_type + pair_cross_type
    L.append(f"- **Same-type pairs:** {pair_same_type} ({100.0 * pair_same_type / total_shared:.1f}%)")
    L.append(f"- **Cross-type pairs:** {pair_cross_type} ({100.0 * pair_cross_type / total_shared:.1f}%)")
    L.append("")

    L.append("### 12. Cross-level sharing")
    L.append("")
    total_band = pair_same_band + pair_cross_band
    L.append(f"- **Same 20-level band pairs:** {pair_same_band} ({100.0 * pair_same_band / total_band:.1f}%)")
    L.append(f"- **Cross-band pairs:** {pair_cross_band} ({100.0 * pair_cross_band / total_band:.1f}%)")
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

    # --- SCOPE NOTE ---
    L.append("## SCOPE: resources-only")
    L.append("")
    L.append(
        "This profile uses the **resources-only** recipe view throughout. "
        "The loader (`EquipmentLoader._parse_recipe`) keeps only recipe entries "
        "with `item_subtype == 'resources'`, dropping equipment and consumables "
        "entries. This is intentional: non-resource entries (quest gear, "
        "consumables) add complexity to the shopping list without contributing "
        "to the resource-sharing structure that grouping measures. They are "
        "not profiled here."
    )
    L.append("")
    L.append(
        f"Raw recipe entries by subtype: "
        f"{', '.join(f'{st}={cnt}' for st, cnt in sorted(subtype_counts.items(), key=lambda x: -x[1]))}. "
        f"{len(items_with_non_resource)} of {n} items "
        f"({100.0 * len(items_with_non_resource) / n:.1f}%) carry at least one "
        f"non-resource entry."
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
        f"1. **Resource breadth is right-skewed.** The median resource is used by "
        f"{fmt(breadth_stats['median'])} items, but the p90 is {fmt(breadth_stats['p90'])} "
        f"and the max is {fmt(breadth_stats['max'])}. Most resources are rare; "
        f"a small number are shared widely."
    )
    L.append(
        f"2. **Resource depth is also right-skewed.** The median resource contributes "
        f"{fmt(ad_stats['median'])} units per item, but the p90 is {fmt(ad_stats['p90'])} "
        f"and the max is {fmt(ad_stats['max'])}. A few resources dominate the "
        f"unit count of their consumers."
    )
    L.append(
        f"3. **Breadth and depth are independent axes.** Of the "
        f"{len(classes.get('broad_heavy', []))} broad+heavy, "
        f"{len(classes.get('broad_medium', []))} broad+medium, and "
        f"{len(classes.get('broad_trivial', []))} broad+trivial resources, "
        f"no single resource dominates all three dimensions. The classes describe "
        f"different sharing patterns, not a single 'constraint' type."
    )
    L.append(
        f"4. **{len(dead_ends)} resources are single-use.** They stay single-use "
        f"under both scopes ({dead_still_single} of {len(dead_ends)}). But "
        f"{len(boss_sharing)} of {len(boss_items)} items consuming them still "
        f"share other resources with the pool, forming {len(boss_pairs)} "
        f"cross-item pairs. Single-use does not mean isolated."
    )
    L.append(
        f"5. **Sharing is sparse.** Only "
        f"{100.0 * len(total_candidate_pairs) / total_pairs:.1f}% of all pairs "
        f"share even one resource. The median Jaccard among candidate pairs is "
        f"{jaccard_stats['median']:.2f}, and the p90 is {jaccard_stats['p90']:.2f}."
    )
    L.append(
        f"6. **Break density increases with level.** The median break density "
        f"rises from {fmt(bd_by_band_stats[0]['median'])} in band 0 to "
        f"{fmt(bd_by_band_stats[max(bd_by_band_stats)]['median'])} in the highest band. "
        f"Higher-level items carry more stat value per item."
    )
    L.append(
        f"7. **Non-resource recipe entries are excluded by design.** "
        f"{len(items_with_non_resource)} of {n} items "
        f"({100.0 * len(items_with_non_resource) / n:.1f}%) carry equipment or "
        f"consumables in their recipe. These are dropped by the loader because "
        f"they add shopping-list complexity without contributing to resource "
        f"sharing."
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
