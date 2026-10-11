# Processing Pipeline Audit

**Date:** 2026-10-10
**Scope:** Active processing pipeline after metric consolidation and method removal.
**Snapshot:** 3.7.7.6 (2858 equipment, 1642 resources, 3646 set mappings)

---

## 1. Pipeline architecture

```
Input pool (2858 items)
    |
    v
SetExclusionFilter (k=5) --> 2364 items (494 set items removed, C2)
    |
    v
RuneMaster.__init__
    |-- OverlapObjective (quality weights)
    |-- GroupAcceptancePolicy (thresholds)
    |-- Experts: deterministic, random, greedy
    |
    v
run_*() method
    |
    v
Groups --> ProcessingReporter --> Summary
```

**Active methods:** `greedy` (default), `deterministic`, `random`, `survey`
**Removed methods:** `genetic`, `evolutionary_committee`, `committee`, `baseline` (commit 82a32ba), `hybrid` (commit c76ce1e)

---

## 2. How each method serves the goal

**Goal:** make breaking many items easier. C1 large groups, C2 no set items, C3 shared resources.

**Reproducibility caveat:** only `greedy` is deterministic. `deterministic`,
`random`, and `survey` read `random_seed` (default `None`), so the numbers below
are single samples and are not reproducible. Measured on two consecutive
`random_seed=None` runs: `deterministic` 97 then 109 groups, `random` 16 then 8,
`survey` 285 then 288. Greedy returned 179 groups / 1406 covered on every run,
under both `None` and `0`. See `processing/PROCESSING.md` §Measured Coverage.

### Greedy (default)

| Aspect | Value |
|--------|-------|
| Coverage | 59.48% (1406/2364) |
| Groups | 179 |
| CV | 0.588 |
| Size median | 8 |
| Shared median | 10 |
| Union median | 18 |
| Compression | 0.500 |
| Cells | 161/178 |
| Time | 24.7s |

**Serves C1/C3 directly.** Builds its own neighbour index from `recipe_resource_ids` (not graph-bound), grows groups against `OverlapObjective` until `max_line_items=32` or `group_max_size=12`. Best coverage, best CV, best cell coverage. The only method that reaches items with no graph edges.

**Gap:** 958 items uncovered — and it is NOT a singleton problem. Measured on the
shipped expert (instrumented replay of `discover_groups`, 2026-10-11): 240 seeds
grew nothing (below `group_min_size`), but 796 groups **were grown and then
rejected by `GroupAcceptancePolicy`** — 733 on `max_line_items`, 53 on
`max_total_units`, 10 on `shared_resources_count`. Of the 958 uncovered, only 2
have an empty recipe and 1 is truly isolated; 949 still have a free partner
(median 204 partners, 953 with >=3). They are excluded by the shopping-effort
budget, not unreachable. See §12.

### Deterministic

| Aspect | Value |
|--------|-------|
| Coverage | 45.85% (1084/2364) |
| Groups | 93 |
| CV | 0.965 |
| Size median | 12 |
| Shared median | 10 |
| Union median | 20 |
| Compression | 0.557 |
| Cells | 118/178 |
| Time | 9.0s |

**Serves C1/C3 but graph-bound.** Builds Jaccard graph at `graph_min_shared_ratio=0.15`, detects Louvain communities, splits into policy-compliant groups. Higher compression (0.557 vs 0.500) but lower coverage. Fast (9.0s).

**Limitation:** reachability is fine at the default ratio. Measured on the full
pool: ratio 0.15 leaves 18/2858 (0.63%) with no edge, ratio 0.3 leaves 408/2858
(14.28%) — matching config.py's comment and the wiki. On the post-set-filter
pool (2364) it is 25 (1.06%) vs 394 (16.67%). Note the 408 figure is the
**full-pool, ratio-0.3** number, not a property of the active configuration.
Graph construction is not the bottleneck at 0.15; the acceptance budget is (§12).

### Random

| Aspect | Value |
|--------|-------|
| Coverage | 2.83% (67/2364) |
| Groups | 15 |
| CV | 1.492 |
| Size median | 4 |
| Shared median | 7 |
| Union median | 16 |
| Compression | 0.400 |
| Cells | 39/178 |
| Time | 0.7s |

**Baseline only.** Stochastic seed-and-grow with `RandomGroupBuilder`. Not a production method -- exists for comparison and as a fallback for `survey`. Negligible coverage.

### Survey

| Aspect | Value |
|--------|-------|
| Coverage | 65.65% (1552/2364) |
| Groups | 286 |
| CV | 0.524 |
| Size median | 10 |
| Shared median | 10 |
| Union median | 19 |
| Compression | 0.525 |
| Cells | 170/178 |
| Time | 33.2s |

**Diagnostic only.** Runs all experts, deduplicates by fingerprint, tags each group with `origins`. Coverage is the union of all experts, not a production method. Use to understand expert disagreement.

**Note:** the 65.65% figure is a single unseeded sample. With `random_seed=0` the union is 287 groups / 1561 covered / 66.03%.

---

## 3. How metrics are consolidated

### Challenge metrics (M1-M9)

Implemented in `analysis/challenge_metrics.py`. All API-computable, no prices/taux/rarity.

| Metric | What it measures | Where used |
|--------|-----------------|------------|
| M1 | Coverage, band-stratified | Challenge evaluation |
| M2 | Band uniformity (CV of M1) | Challenge evaluation |
| M3 | Ubiquity-weighted shared resources | Challenge evaluation |
| M4 | Hub concentration (Goodhart detector) | Challenge evaluation |
| M5 | Pod load (carrying constraint) | Challenge evaluation |
| M6 | Slot and slot x band coverage | Challenge evaluation |
| M7 | Group-size and sharing profile | Challenge evaluation |
| M8 | Recipe-subtype leakage | Challenge evaluation |
| M9 | Between-group overlap | Challenge evaluation |

### Pipeline metrics (existing)

| Metric | Location | Purpose |
|--------|----------|---------|
| `sharing_efficiency` | `GroupMetrics` | Pairwise/aggregate Jaccard |
| `quality_score` | `GroupQualityEvaluator` | Weighted blend: compression + shared_quantity + set_free - largest_set |
| `compression` | `ShoppingList` | 1 - |U| / sum|R_i| |
| `set_free_ratio` | `GroupQualityEvaluator` | Reward for setless items |
| `largest_set_share` | `GroupQualityEvaluator` | Penalty for set concentration |
| `break_density` | `valuation/focus.py` | Stat value per item |
| `equipment_coverage_rate` | `PortfolioQualityEvaluator` | Portfolio-level coverage |

### Derived data (A1-A4)

| Data | Source | Cost |
|------|--------|------|
| A1 pods per resource | `resources.data` | 0 |
| A2 recipe-subtype split | `equipment.data` | 0 |
| A3 resource level | `resources.data` | 0 |
| A4 resource breadth | derived from equipment | 0 |

---

## 4. Filters

| Filter | Default | Purpose |
|--------|---------|---------|
| `SetExclusionFilter` | k=5 | C2: remove set items before any expert runs |
| `JobLevelFilter` | off | Craftability by player profession levels |
| `EquipmentFilteringStrategy` | **inert** | `use_density_filtering`/`equipment_density_level_ratio`/`fallback_to_unfiltered` are never read by the pipeline; `density_percentile` (default 0.0) is the live gate |
| `excluded_resource_ids` | {14635} | Pepite excluded from sharing (not from shopping list) |

---

## 5. Valuation (swappable objective seam)

| Class | Role | Used by |
|-------|------|---------|
| `GroupObjective` (Protocol) | score() + marginal() | All experts |
| `OverlapObjective` | Wraps `GroupQualityEvaluator` | All experts |
| `GroupCandidate` | Immutable group + with_item() | All experts |
| `FlatTauxModel` | Placeholder taux | `ProfitObjective` |
| `PosteriorTauxModel` | Break-outcome taux | `ProfitObjective` (future) |
| `ProfitObjective` | Full profit objective | Not active (no prices) |
| `NullPriceSource` | No prices | Default |
| `CachePriceSource` | Cached prices | Future |
| `break_density()` | Stat weight per item | Greedy expert |

---

## 6. Blocks (pure helpers)

| Module | Key functions |
|--------|---------------|
| `blocks/similarity.py` | `jaccard()` |
| `blocks/shopping_list.py` | `ShoppingList`, `merge()`, `resource_totals()` |
| `blocks/recipes.py` | `iter_recipe()`, `recipe_resource_ids()`, `_build_inverted_index()` |

---

## 7. Graph pipeline

| Module | Key functions |
|--------|---------------|
| `graph/graph_builder.py` | `build_equipment_graph()`, `create_jaccard_similarity_graph()` |
| `graph/community_detector.py` | `find_best_louvain_partition()`, `find_best_bilouvain_partition()` |
| `graph/group_mapper.py` | `map_communities()`, `_split_large_community()` |

Used by: `deterministic` expert, `survey` method. NOT used by `greedy` or `random`.

---

## 8. Tools (not runtime pipeline)

| Module | Purpose |
|--------|---------|
| `tools/tuner.py` | Offline parameter search |
| `tools/harness.py` | Offline method comparison |

---

## 9. Config defaults (verified correct)

| Field | Default | Evidence |
|-------|---------|----------|
| `grouping_method` | `"greedy"` | Best coverage/CV/cells |
| `graph_min_shared_ratio` | `0.15` | Correct, but for the reason config.py already states: 0.3 would leave 408 items (14.28%) with no edge. Keep. |
| `max_line_items` | `32` | 3.6x coverage vs 12 |
| `max_total_units` | `2000` | **Not** secondary: lifting it alone gives +3.04pp (1478 covered). It rejects 53 groups the line-item cap would allow. |
| `set_exclusion_min_size` | `5` | Correct (5.25pp cost is deliberate C2) |
| `group_max_size` | `12` | Reachable at mli=32 |
| `group_min_size` | `2` | Standard |
| `group_min_shared_resources` | `3` | Discriminates weak end |
| `group_efficiency_threshold` | `0.15` | Live at policy.py:55, gated to `group_size <= 3` |
| `group_quality_threshold` | `0.0` | No quality gate |
| `group_max_set_share` | `0.5` | Guards boundary |
| `excluded_resource_ids` | `{14635}` | Pepite excluded from sharing |
| `use_density_filtering` | `True` (unread) | Declared but never consumed; `density_percentile=0.0` means no density gate is applied |
| `fallback_to_unfiltered` | `False` (unread) | Declared but never consumed |
| `use_job_level_filter` | `False` | Job filtering off by default |

---

## 10. Known gaps and future work

| Gap | Impact | Status |
|-----|--------|--------|
| **Group rejection by the shopping budget, not singleton discards** | 59.48% -> 90.02% by lifting `max_line_items` + `max_total_units`; 240 singleton seeds and 796 policy-rejected grown groups. This supersedes the earlier "257 singleton discards" entry. | Open (see §12) |
| `resource_reuse_ratio` still in quality_score | Already weight 0.0 and normalized out — harmless, but still in `REWARD_FIELDS` | Open (see quality-score-reweighting plan) |
| `group_efficiency_threshold` mis-scoped | Only discriminates at g=2,3 | Open |
| No prices/taux | Profit objective not computable | Blocked on external data |
| Dead config fields | `min_filtered_pool_size`, `min_equipment_density`, `flat_taux`, `price_max_age_seconds`, `dedup_overlap_threshold` are declared but never read anywhere | Open |
| Non-reproducible method metrics | Only `greedy` is seed-independent; `deterministic`, `random`, `survey` vary run to run at the default `random_seed=None`. Every published number for those three needs its seed stated | Open |
| `equipment_density_level_ratio` / `use_density_filtering` / `fallback_to_unfiltered` never read | The density filter is inert. `density_percentile` is the live lever (default 0.0 = off) | Open — audit §4/§9 saying it is "on" is wrong |
| Two data paths disagree | `from_raw_batch` (live) drops 86 items with `stat_weight <= 0`; `load_snapshot` keeps them. Snapshot and live pools are not the same population | Open |
| `run_hybrid_grouping` refs survive in `analysis_sweep.py` and `scripts/phase1_measurement.py` | Offline scripts crashed with `AttributeError` (the method was removed) | **Fixed** — both dispatch tables now list `survey` |
| `challenge_coverage_gap.py` re-implemented the greedy loop and omitted the policy gate | Its output was internally impossible (`coverage_if_singletons_kept = 1.0233`) and mis-attributed the gap to singletons | **Fixed** — now runs the shipped expert and asserts its own invariants |


---

## 11. Summary

The pipeline is in a mostly clean state:

- **4 active methods** (greedy, deterministic, random, survey) with clear roles
- **3 active experts** (deterministic, random, greedy) behind a common `GroupingExpert` ABC
- **Swappable objective** via `GroupObjective` protocol
- **Consolidated metrics** in `analysis/challenge_metrics.py` (M1-M9)
- **140 tests passing**, compileall clean, `git diff --check` clean
- **Not** free of dead code: `hybrid` still referenced by two offline scripts, five config fields are unread, and the density filter is inert

The highest-impact lever is **not** singleton assignment (it changes nothing —
`group_min_size=1` leaves coverage at 59.48% because the greedy loop only returns
singletons where it has no admissible partner). It is the shopping budget:
lifting `max_line_items` and `max_total_units` together reaches 90.02%.

---

## 12. Measured findings (2026-10-11)

All numbers below come from running the shipped pipeline against snapshot 3.7.7.6
in-process (`uv run python`), not from a re-implementation or a simulation.

**Coverage-gap attribution** — instrumented replay of
`GreedyGroupingExpert.discover_groups` with the real `GroupAcceptancePolicy`:

```
pool (post set-filter)     2364
accepted groups             179
covered                    1406  (59.48%)
singleton seeds (< min)     240
grown but policy-rejected   796   <- max_line_items 733
                                     max_total_units 53
                                     shared_resources_count 10

uncovered                   958
  empty recipe                2
  truly isolated              1
  orphaned (partners covered) 6
  partners exist, all free  949   (median 204 partners, 953 with >=3)
```

**Coverage levers** — same pool, one config field changed at a time:

```
baseline (mli=32, mtu=2000, gmin=2)      groups=179 covered=1406 cov=59.48%
max_line_items=10000                     groups=217 covered=1881 cov=79.57%
max_total_units=1e9                      groups=188 covered=1478 cov=62.52%
both caps lifted                         groups=241 covered=2128 cov=90.02%
group_min_size=1                         groups=179 covered=1406 cov=59.48%
group_max_size=24 + mli lifted           groups=174 covered=1880 cov=79.53%
greedy_candidate_limit=200               groups=159 covered=1315 cov=55.63%
```

`max_total_units` is a real constraint, not a secondary lever: on its own it is
worth +3.04pp. `greedy_candidate_limit=200` is worse than the default 25.

**Graph reachability** — measured before component filtering:

```
full pool        n=2858 ratio=0.15 no-edge= 18 (0.63%)  ratio=0.3 no-edge=408 (14.28%)
post set-filter  n=2364 ratio=0.15 no-edge= 25 (1.06%)  ratio=0.3 no-edge=394 (16.67%)
```

**Documentation drift** — `processing/PROCESSING.md` config table still lists
pre-consolidation defaults: `group_max_size=32` (actual 12), `max_line_items=12`
(actual 32), `max_total_units=500` (actual 2000), `graph_min_shared_ratio=0.3`
(actual 0.15). It also omits `equipment_density_level_ratio`,
`set_exclusion_min_size`, `use_density_filtering`, and `fallback_to_unfiltered`.

