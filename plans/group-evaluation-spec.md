# Group-Evaluation Spec: Metrics for Comparing Grouping Methods

**Scope:** Comparing candidate grouping methods on two axes — (A) shopping-list efficiency and (B) exploration diversity — without picking weights or editing code.

**Core insight from docs/02:** The objective is profit from a craft-break-sell loop. Shopping-list compactness is not the goal — it is the lambda term inside the profit equation. Diversity is not a nice-to-have — it is the only mechanism for discovering high-taux items.

---

## 1. Candidate Metrics

### Axis A — Shopping-List Efficiency

| # | Metric | Formula | Inputs available today | What it fails to capture |
|---|--------|---------|------------------------|--------------------------|
| A1 | **Compression** | `1 - |U| / S` where U = union of resource IDs, S = sum of per-item recipe sizes | `equipment.recipe` (resource IDs via `iter_recipe`) | Does not distinguish a shared resource used 50x from one used 2x. Ignores resource rarity. |
| A2 | **Resource Reuse Ratio** | `|shared| / |U|` where shared = resources used by >=2 items | `equipment.recipe` | Penalizes large groups (denominator grows). Ignores quantities — a shared resource counted the same whether it appears once or 100x. |
| A3 | **Shared Quantity Ratio** | `sum(q_r for r in shared) / sum(q_r for all r)` | `equipment.recipe` (quantities) | Biased toward groups where one heavy resource dominates. Ignores how many items benefit. |
| A4 | **Items per Line Item** | `|G| / |U|` | `equipment.recipe` | Pure count ratio; does not distinguish a 10-item/2-resource group from a 10-item/10-resource group where 2 resources happen to be shared. |
| A5 | **Unique Resource Count** | `|U|` | `equipment.recipe` | Raw count; no normalization. Rewards tiny groups. |
| A6 | **Total Units Needed** | `sum(q_r for r in all r)` | `equipment.recipe` | Raw quantity; no per-item normalization. Ignores bulk-purchase price impact. |
| A7 | **Acquisition Cost Proxy** | `lambda * |U|` | `equipment.recipe` + user-provided lambda | Assumes uniform per-resource cost; ignores resource rarity, bulk discounts/penalties, and order-book depth. |

### Axis B — Exploration Diversity

| # | Metric | Formula | Inputs available today | What it fails to capture |
|---|--------|---------|------------------------|--------------------------|
| B1 | **Largest Set Share** | `max_set_count / |G|` | `equipment.set_id` | Binary proxy for taux. Does not distinguish two sets at 50% from one set at 90%. Ignores item level spread. |
| B2 | **Set-Free Ratio** | `count(set_id is None) / |G|` | `equipment.set_id` | Counts only fully setless items; a 3-set group and a 2-set group with the same set-free count score identically. |
| B3 | **Distinct Set Count** | `|{set_id : set_id is not None}|` | `equipment.set_id` | Does not capture how items are distributed across sets. A 10-set group with one item per set scores the same as a 10-set group with one set having 19 items. |
| B4 | **Set Entropy** | `-sum(p_s * log(p_s))` where p_s = items in set s / total | `equipment.set_id` | Needs a normalization convention for set-free items (own category or excluded). Insensitive to level spread within sets. |
| B5 | **Level Spread** | `std(item.levels)` or `(max - min)` | `equipment.level` | Does not capture whether the spread is clustered or uniform. Two groups with same std can have very different exploration profiles. |
| B6 | **Level Coverage** | `|{item.level}|` | `equipment.level` | Raw count; does not indicate whether levels are clustered in one band or spread across the playable range. |
| B7 | **Distinct Break Density Range** | `std(break_density(item))` | `equipment.effects` + `RUNE_DENSITY` (via `break_density`) | Measures output diversity, not input diversity. Two items can have different stats but identical density. Ignores rune-type diversity. |
| B8 | **Rune-Type Coverage** | `|{stat_type for all stat lines in group}|` | `equipment.effects` (stat types) | Does not weight by density or price. A group with 5 minor-rune stats scores the same as one with 5 high-density stats. |
| B9 | **Recipe Diversity** | `|U_group| / sum(|R_i|)` = inverse of compression (A1) | `equipment.recipe` | This is the inverse of A1 — recipe diversity is the cost side of shopping-list efficiency, not exploration diversity per se. |

---

## 2. Portfolio-Level Metrics

These evaluate a complete algorithm output (set of groups) rather than a single group.

| # | Metric | Formula | Inputs available today | What it fails to capture |
|---|--------|---------|------------------------|--------------------------|
| P1 | **Equipment Coverage Rate** | `|union of all group equipment| / |total equipment pool|` | `equipment.ankama_id` across groups | Does not account for equipment that is craftable but excluded by policy. |
| P2 | **Assignment Overlap Rate** | `1 - |union| / sum(|group|)` | `equipment.ankama_id` across groups | Measures redundancy but not whether overlapping items are the high-value ones. |
| P3 | **Mean Group Quality** | `mean(quality_score(g) for g in groups)` | `quality_score` from `GroupQualityWeights` | Dominated by the current proxy weights. Equal weight to small and large groups. |
| P4 | **Assignment-Weighted Quality** | `sum(quality_score(g) * |g|) / sum(|g|)` | `quality_score` + group sizes | Favors methods that produce many small groups. |
| P5 | **Portfolio Resource Overlap** | `sum(|U_i intersect U_j|) / sum(|U_i union U_j|)` across group pairs | `equipment.recipe` | Does not distinguish overlap on cheap common resources from overlap on expensive rare ones. |
| P6 | **Slot Coverage** | `|{item.type for all items in portfolio}| / |total types in pool|` | `equipment.type` | Does not weight by type importance. A portfolio covering 3 of 5 types scores the same whether the missing types are critical or marginal. |
| P7 | **Level Band Coverage** | `|{level_band(item)}| / |total bands|` where band = floor(level/20) | `equipment.level` | Arbitrary band boundaries. Does not capture whether covered bands are the profitable ones. |
| P8 | **Mean Pairwise Group Jaccard** | `mean(jaccard(equip_sets))` across group pairs | `equipment.ankama_id` | Only measures equipment overlap, not resource overlap. Two groups can share zero equipment but 100% of resources. |

---

## 3. Metric Availability Status

### Already computed in the codebase

| Metric | Location | Notes |
|--------|----------|-------|
| A1 Compression | `quality_metrics.py` via `GroupQualityEvaluator` | Core feature, weighted in quality score |
| A2 Resource Reuse Ratio | `quality_metrics.py` via `GroupQualityEvaluator` | Core feature, weighted in quality score |
| A3 Shared Quantity Ratio | `quality_metrics.py` via `GroupQualityEvaluator` | Core feature, weighted in quality score |
| A4 Items per Line Item | `group_metrics.py` via `GroupMetrics.build_group_dict` | Reported as `items_per_line_item` |
| A5 Unique Resource Count | `quality_metrics.py` + `group_metrics.py` | `unique_resource_count` / `unique_ingredients_count` |
| A6 Total Units Needed | `group_metrics.py` via `GroupMetrics.build_group_dict` | Reported as `total_items_needed` |
| B1 Largest Set Share | `quality_metrics.py` via `_set_membership_features` | `largest_set_share`, penalized in quality score |
| B2 Set-Free Ratio | `quality_metrics.py` via `_set_membership_features` | `set_free_ratio`, weighted in quality score |
| B3 Distinct Set Count | **Not computed** | Derivable from `equipment.set_id` |
| B5 Level Spread | **Not computed** | Derivable from `equipment.level` |
| B7 Distinct Break Density Range | **Not computed** | Derivable from `break_density(equipment)` |
| B8 Rune-Type Coverage | **Not computed** | Derivable from `equipment.effects` |
| P1 Equipment Coverage Rate | `quality_metrics.py` via `PortfolioQualityEvaluator` | `equipment_coverage_rate` |
| P2 Assignment Overlap Rate | `quality_metrics.py` via `PortfolioQualityEvaluator` | `assignment_overlap_rate` |
| P3 Mean Group Quality | `quality_metrics.py` via `PortfolioQualityEvaluator` | `mean_group_quality` |
| P4 Assignment-Weighted Quality | `quality_metrics.py` via `PortfolioQualityEvaluator` | `assignment_weighted_group_quality` |
| P5 Portfolio Resource Overlap | **Not computed** | Derivable from group recipes |
| P6 Slot Coverage | **Not computed** | Derivable from `equipment.type` |
| P8 Mean Pairwise Group Jaccard | `quality_metrics.py` via `PortfolioQualityEvaluator` | `mean_group_overlap` |

### New metrics (derivable from existing data, not yet computed)

- **B3 Distinct Set Count** — one-liner over `equipment.set_id`
- **B4 Set Entropy** — requires deciding how to categorize set-free items
- **B5 Level Spread** — `statistics.stdev(item.levels)`
- **B6 Level Coverage** — `len(set(item.levels))`
- **B7 Distinct Break Density Range** — `statistics.stdev(break_density(e))`
- **B8 Rune-Type Coverage** — `len({s.stat_type for e in group for s in e.effects})`
- **P5 Portfolio Resource Overlap** — Jaccard on resource unions across group pairs
- **P6 Slot Coverage** — set of `equipment.type` across portfolio
- **P7 Level Band Coverage** — set of `floor(level / band_width)` across portfolio

### Metrics that need data we do NOT have yet

| Metric | Missing data | Why it matters |
|--------|-------------|----------------|
| A7 Acquisition Cost Proxy | `lambda` (user-calibrated) + resource prices | Without lambda, A1-A6 are unweighted proxies. Without resource prices, cannot distinguish cheap-common from expensive-rare resources. |
| B1-B9 Diversity-weighted-by-value | Rune prices (`rho_f`) | Diversity is only valuable if the runes it discovers are worth selling. |
| Any profit-estimate metric | `rho_f` + `c_i` + `tau` + `n_i` | The true objective. Cannot be computed until Phase 3. |
| Order-book impact metric | Market depth data | Needed to penalize large-volume resource purchases. |

---

## 4. Goodhart Risks (How Each Metric Can Be Gamed)

| Metric | Gaming strategy | Why it works |
|--------|-----------------|--------------|
| A1 Compression | Create one mega-group with all items sharing 1-2 trivially common resources | Compression approaches 1 as long as union stays small. No penalty for including junk items. |
| A2 Resource Reuse Ratio | Keep groups small (2-3 items) so denominator stays small | Reuse ratio is maximized at small group sizes. Incentive to fragment. |
| A3 Shared Quantity Ratio | Find one resource that appears in huge quantities across many items, ignore the rest | One heavy shared resource dominates the ratio. |
| A4 Items per Line Item | Add items that reuse existing resources but contribute nothing valuable | Rewards quantity of items, not quality. |
| B1 Largest Set Share | Spread items evenly across many sets even if some sets are poor exploration targets | Low concentration does not mean high exploration value. |
| B3 Distinct Set Count | Include one item from every set regardless of level or stats | Rewards set-counting, not exploration quality. |
| B5 Level Spread | Include one very high-level item and one very low-level item | Std is maximized by extremes, not by useful coverage. |
| B7 Break Density Range | Pair one item with a very high-density stat and one with a very low-density stat | Std is maximized by extremes, not by profit-relevant diversity. |
| P1 Equipment Coverage Rate | Assign every item to at least one group, even if some assignments are worthless | Coverage counts presence, not quality. |
| P3 Mean Group Quality | Produce many small groups that each score well on the current proxy | Mean is sensitive to group count. Small groups inflate the average. |
| P8 Mean Pairwise Group Jaccard | Make all groups share a common core of 2-3 items | Inflates overlap metric without meaningful resource sharing. |

**Systemic risk:** Any single-metric evaluation will be gamed. The current `quality_score` is a weighted blend of A1, A2, A3, B1, B2 — an optimizer that maximizes this blend will find the sweet spot of those five proxies and ignore everything else. This is the core argument for a minimal metric set that spans both axes.

---

## 5. Recommended Minimal Set (7 metrics)

This set spans both axes, resists individual gaming, and can be computed entirely from data available today.

### Axis A — Shopping-List Efficiency (3 metrics)

| # | Metric | Rationale |
|---|--------|-----------|
| A1 | **Compression** | The only A-metric that is extensive (increases with group size). Direct stand-in for the lambda term. Resists the "tiny group" gaming of A2. |
| A3 | **Shared Quantity Ratio** | The only A-metric that accounts for quantities, not just binary presence. Catches cases where A1 is inflated by trivial overlaps. |
| A5 | **Unique Resource Count** | The raw material cost denominator. Catches groups that game A1/A3 by adding many items that share nothing. |

### Axis B — Exploration Diversity (3 metrics)

| # | Metric | Rationale |
|---|--------|-----------|
| B1 | **Largest Set Share** | The only B-metric already in the quality score. Direct proxy for taux risk. Catches set-concentration gaming of B2. |
| B3 | **Distinct Set Count** | Rewards genuine spread across panoplies. Resists the "even spread across bad sets" gaming of B1. |
| B5 | **Level Spread** | Catches the "same-level clone" failure mode. Two groups with identical set composition but different level profiles are not equally valuable. |

### Portfolio-Level (1 metric)

| # | Metric | Rationale |
|---|--------|-----------|
| P1 | **Equipment Coverage Rate** | The only portfolio metric that cannot be gamed by producing many small groups. Measures whether the algorithm is actually assigning the pool. |

### Why these 7 and not others

- **A2 Resource Reuse Ratio** is redundant with A1 and A3 — it is bounded by their product and adds no independent signal.
- **A4 Items per Line Item** is a ratio of A5 to group size; it adds normalization but no new information.
- **A6 Total Units Needed** is important for bulk-cost modeling but is not computable without prices and is not a diversity measure.
- **B2 Set-Free Ratio** is a special case of B1 (if all items are set-free, B1 = 0).
- **B4 Set Entropy** is better than B1+B3 in theory but requires a normalization convention for set-free items that we have not agreed on.
- **B7 Break Density Range** and **B8 Rune-Type Coverage** are output-diversity metrics; they are valuable but secondary to input-diversity metrics because output diversity without profit data is uninterpretable.
- **P5 Portfolio Resource Overlap** is valuable for the "combined shopping list" use case but requires cross-group analysis that is not yet implemented.

---

## 6. Open Questions

1. **How should set-free items be treated in set-based diversity metrics?** As their own category (increasing B3), as a separate flag (B2), or excluded from the denominator?

2. **Should level bands be fixed (e.g., 0-50, 50-100, 100-150, 150-200) or data-driven (percentiles of the equipment pool)?** Fixed bands are interpretable but may split natural clusters. Data-driven bands adapt but change as the pool grows.

3. **Is "resource rarity" available in the API data?** If resources have a rarity or drop-rate field, it should weight A1-A5. A shared common resource is less valuable than a shared rare one.

4. **Should the minimal set be expanded to include one output-diversity metric (B7 or B8) once `break_density` is validated?** Output diversity is closer to the true objective but harder to interpret without prices.

5. **How should these metrics be reported?** As a raw table (one row per method, one column per metric), or as a normalized radar chart? Raw tables are precise; radar charts reveal trade-offs at a glance.

6. **Does `equipment.type` map to a small, stable set of slots (weapon, helmet, amulet, etc.)?** If so, P6 Slot Coverage is a high-value addition. If types are fine-grained, it may be noisy.

7. **Should portfolio-level metrics be computed on the full algorithm output or on a policy-filtered subset?** Filtering removes invalid groups but may hide systematic policy-violation patterns.
