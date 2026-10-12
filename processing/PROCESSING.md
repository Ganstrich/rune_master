# Processing Module

This document is the authoritative functional specification for group creation
in RuneMaster. It describes the behavior implemented under `processing/` and
the dispatch performed by `main.py`. A change to group construction, filtering,
scoring, selection, or configuration is incomplete until this file and its
contract tests are updated in the same change.

Every default and code reference in this file was verified against
`processing/config.py` and the module it names. Where a number is empirical it
carries the snapshot it was measured on.

## Purpose And Boundaries

RuneMaster receives loaded `Equipment` objects and proposes small sets of items
whose recipes reuse resource types. This stage does not fetch equipment, compute
market profit, estimate rune yield, or reduce the quantities required by a
recipe. Resource metadata from the cache affects display fields only; it never
affects membership or scores.

Each input equipment is expected to provide:

- a unique `ankama_id`;
- `level` and an optional precomputed `stat_weight`;
- a recipe containing `(resource_id, quantity)` requirements.

`data.loaders` calculates stat weights and applies `min_equipment_density` and
`density_percentile` before this module is called. Within `processing/`, no
expert applies density filtering: `EquipmentFilteringStrategy` is retained but
is not wired into the runtime pipeline (see "Inert Filters" below).

## Job-Level Filtering

Crafting an item requires a minimum job (profession) level, so a group the
player cannot craft is useless. `main.py::apply_job_level_filter()` drops
such equipment before `RuneMaster` is constructed, so every expert, the
acceptance policy, and the report operate on the craftable pool only.

The predicate lives in `processing/filters/job_filter.py`:

```
craftable(item) = job_levels[job_for(item.type)] >= item.level
```

- An item at exactly the job level is craftable (`>=`, not `>`).
- An item whose type maps to no known job is **kept**. A new item type must
  not silently vanish from the report.
- An item whose job is not in `job_levels` is **kept**. Partial
  configurations are not silently destructive.

The job-to-type mapping is the `CORDONNIER`, `BIJOUTIER`, `TAILLEUR`,
`FORGERON`, `SCULPTEUR`, and `FACONNEUR` lists in `config.py`. Each
craftable type belongs to exactly one job; a unit test asserts the mapping
is total over `ALL_CRAFTABLE_TYPES`.

**Type resolution.** The DofusDB API filter takes an English `name_id`
(`sword`, `ring`, ...) while the equipment payload carries a French display
name and a numeric id (`{"name": "Épée", "id": 80}`). `resolve_job()` matches
the numeric id first, then the name, so a live API run and a frozen-snapshot
run resolve identically regardless of language. `ITEM_TYPE_IDS` is the
name_id-to-numeric-id table and the single place to extend for a new type.

Filtering is off by default (`use_job_level_filter=False`), preserving the
full pool. Levels come from `player_config.json` in the project root, or
`--job-levels "forgeron:120,bijoutier:80"` on the CLI, which overrides the
file per job. `--no-job-filter` disables filtering for one run. The effective
levels and the kept/filtered counts are recorded in the run manifest under
`job_filter`.

## Panoplie Set Exclusion

Constraint C2: groups must not be built from panoplie items, because set items
are the systematically over-crafted, low-taux choices. `SetExclusionFilter`
applies this once in `RuneMaster.__init__`, before any expert runs, so every
`run_*` path sees the same pool.

An item is excluded when its panoplie has at least `set_exclusion_min_size`
members **present in the pool being filtered**. Membership counts are computed
from the supplied list, not from a global index, so the exclusion is relative
to the loaded scope. `set_exclusion_min_size=99` or higher disables the filter.

The removal is reported through `summarize_excluded()` (metric N10: band and
slot breakdown) and carried in `self.set_exclusion_report`, so a deliberate
scope decision cannot later read as a coverage regression.

Measured on snapshot 3.7.7.6: `k=5` removes 494 of 2858 items (17.28%),
leaving a 2364-item pool.

## End-To-End Dispatch

`main.py::process_equipment()` constructs `RuneMaster` and dispatches from
`ProcessingConfig.grouping_method`:

| Value | Method called | Result |
| --- | --- | --- |
| `deterministic` | `run_deterministic()` | Graph expert only |
| `random` | `run_random_grouping()` | Random expert only |
| `greedy` | `run_greedy()` | Greedy objective-driven expert only (default) |
| `survey` | `run_survey()` | Every expert; union of proposals tagged with their origin |

The CLI restricts the value to those four choices. `run_all()` is a
backward-compatible alias for `run_deterministic()`; calling it directly does
not inspect `grouping_method` and always runs deterministic grouping.

Every accepted proposal is a canonical group dictionary built by
`GroupMetrics.build_group_dict()`. Expert-specific metadata is added afterward.

## Configuration

`ProcessingConfig` (`processing/config.py`) is the runtime configuration
contract. "Consumed by" names the module that actually reads the field; a field
marked **inert** is declared but never read anywhere in the repository.

### Pipeline And Graph

| Field | Default | Consumed by | Exact behavior |
| --- | ---: | --- | --- |
| `grouping_method` | `"greedy"` | `main.py` dispatch | Selects the orchestrator path; `run_all()` ignores it |
| `random_group_count` | `50` | Random expert | Maximum number of generation attempts |
| `random_seed` | `None` | Louvain and random expert | Seeds the corresponding stochastic operations when set |
| `algorithm` | `"louvain"` | Graph expert | `louvain`, `bilouvain`, or any other value for connected components |
| `resolution_range` | `(1, 10, 1)` | Louvain and BiLouvain | Passed to `np.arange(start, stop, step)`; the stop value is excluded |
| `graph_min_shared_ratio` | `0.15` | Jaccard graph paths; not BiLouvain | Minimum pairwise recipe Jaccard for a similarity edge |
| `graph_min_shared_count` | `1` | Jaccard graph paths; not BiLouvain | Minimum absolute shared resource IDs for the same edge; both edge conditions must pass |
| `graph_min_component_size` | `2` | Jaccard graph paths; not BiLouvain | Connected components smaller than this are removed |
| `same_set_edge_discount` | `1.0` | Graph building | Weight multiplier for edges inside one panoplie; `1.0` disables the correction |

The `0.15` ratio is data-backed: at `0.3`, 408 of 2858 items (14.28%) have no
graph edge at all, while `0.15` leaves 18 (0.63%). Both figures are measured on
the full pool; on the post-set-exclusion pool the same comparison is 394
(16.67%) versus 25 (1.06%).

### Experts

| Field | Default | Consumed by | Exact behavior |
| --- | ---: | --- | --- |
| `greedy_candidate_limit` | `25` | Greedy expert | Candidates scored per growth step |
| `greedy_seed_limit` | `0` | Greedy expert | Seeds to expand; zero uses the whole pool |

### Group Acceptance

| Field | Default | Consumed by | Exact behavior |
| --- | ---: | --- | --- |
| `group_min_size` | `2` | All experts | Minimum accepted group size |
| `group_max_size` | `12` | All experts | Upper bound on group size; reached at `max_line_items=32` |
| `group_min_shared_resources` | `3` | All experts | Minimum number of non-excluded resource IDs used by at least two items |
| `group_efficiency_threshold` | `0.15` | Acceptance policy | Minimum legacy `sharing_efficiency`, applied only when `group_size <= 3` |
| `group_quality_threshold` | `0.0` | Acceptance policy | Minimum item-only `quality_score` |
| `group_max_set_share` | `0.5` | Acceptance policy and greedy expert | Maximum share of a group coming from one panoplie |
| `max_line_items` | `32` | Acceptance policy | Maximum distinct resources in the shopping list |
| `max_total_units` | `2000` | Acceptance policy | Maximum total recipe units in the shopping list |
| `use_inclusive_mapping` | `False` | Graph expert | Split oversized communities instead of rejecting them whole; currently unreachable |

`group_max_size=12` is deliberately below the historical `32`: at `max_line_items`
32 the value 32 admitted groups that could never pass the shopping caps.
`max_total_units=2000` is a real constraint, not a secondary one — on snapshot
3.7.7.6 it is the sole rejection reason for 53 grown groups (see "Measured
Coverage" below).

### Filters

| Field | Default | Consumed by | Exact behavior |
| --- | ---: | --- | --- |
| `set_exclusion_min_size` | `5` | `SetExclusionFilter` | Panoplie items in a set of at least this many pool members are dropped before any expert runs; `>= 99` disables |
| `excluded_resource_ids` | `{14635}` | Group filters, quality, random affinity, greedy growth | Resource IDs ignored where explicitly described below |
| `density_percentile` | `0.0` | `data.loaders` only | Within-level-band stat-density percentile; zero disables the gate |
| `density_level_band` | `20` | `data.loaders` only | Level width used for percentile bands |
| `min_equipment_density` | `0.0` | **inert** | Declared as an absolute minimum `stat_weight`; read nowhere |
| `use_density_filtering` | `True` | **inert** | Declared; the runtime pipeline never reads it |
| `equipment_density_level_ratio` | `2.0` | **inert** | Declared; the runtime pipeline never reads it |
| `fallback_to_unfiltered` | `False` | **inert** | Declared; the runtime pipeline never reads it |
| `min_filtered_pool_size` | `10` | **inert** | Declared; read nowhere |
| `use_job_level_filter` | `False` | `main.py` | When true and `job_levels` is populated, drop equipment whose crafting job is below the item level |
| `job_levels` | `{}` | `main.py` | Player job levels by job name (e.g. `{"forgeron": 100}`) |

### Objective, Metrics, And Tools

| Field | Default | Consumed by | Exact behavior |
| --- | ---: | --- | --- |
| `acquisition_cost` | `0.0` | `ProfitObjective` | Kama-equivalent fixed cost per distinct resource |
| `flat_taux` | `1.0` | **inert** | Placeholder constant; `ProfitObjective` uses `FlatTauxModel()` directly, not this field |
| `price_max_age_seconds` | `3600.0` | **inert** | Declared; read nowhere |
| `group_quality_weights` | `0.45 / 0.0 / 0.15 / 0.15` + `0.45` penalty | `GroupQualityEvaluator` | Raw weights for compression, reuse, shared quantity, and set-free share, plus the same-set concentration penalty; see the normalized score below |
| `portfolio_quality_weights` | `0.65 / 0.35 / 0.50` | `ProcessingReporter`, tuner | Group-quality reward, coverage reward, and overlap penalty |
| `dedup_overlap_threshold` | `0.7` | **inert** | Declared for survey de-duplication; `run_survey` de-duplicates by exact equipment fingerprint instead |

The reward fields in both weight dataclasses must be non-negative. Group-quality
weights are normalized to sum to one. Portfolio group-quality and coverage
weights are normalized together; the overlap penalty is not normalized.

### Inert Filters

`processing/filters/equipment_filter.py::EquipmentFilteringStrategy` implements
density-ratio filtering (`filter_by_density_ratio`, `get_active_pool`) with a
small-pool fallback. It is exercised by tests and by
`processing/tools/tuner.py`, but **no runtime path calls it**: `RuneMaster` does
not apply it, and no expert applies it. `use_density_filtering`,
`equipment_density_level_ratio`, and `fallback_to_unfiltered` therefore have no
effect on a `main.py` run. Density gating in production happens only through
`data.loaders` and `density_percentile`.

## Recipe And Resource Semantics

For set-based calculations, a resource can occur at most once per equipment,
even if malformed input repeats it in that recipe. Across a group:

- a resource is **shared** when it appears in at least two equipment recipes;
- recipe Jaccard is `|resources_a intersection resources_b| / |union|`;
- graph construction ignores recipe quantities;
- ingredient aggregation sums recipe quantities.

Exclusions are not applied uniformly during candidate discovery. The Jaccard
similarity graph and BiLouvain projection include every recipe resource,
including configured exclusions. The random expert and the greedy expert remove
exclusions before seed-companion matching. Final group filters and item-only
quality then apply the metric-specific rules below.

### Legacy Sharing Efficiency

`GroupMetrics.sharing_efficiency()` is retained for compatibility and filtering:

```text
sharing_efficiency =
    non_excluded_shared_resource_count / all_unique_resource_count
```

The numerator excludes `excluded_resource_ids`; the denominator includes them.
Consequently, excluded resources cannot help the score but can lower it.

The canonical group fields `shared_resources_count` and
`total_shared_resources` both use the configured exclusions. Despite its legacy
name, `total_shared_resources` is a `set[int]`, not a count and not an inclusive
set of excluded IDs.

### Item-Only Quality Features

`GroupQualityEvaluator` removes excluded IDs from every numerator and
denominator. Negative recipe quantities are clamped to zero for these features.
It emits:

| Feature | Definition |
| --- | --- |
| `group_size` | Number of equipment in the group |
| `unique_resource_count` | Number of distinct non-excluded resource IDs |
| `shared_resource_count` | Non-excluded resource IDs used by at least two equipment |
| `resource_occurrence_count` | Sum of distinct resource occurrences across equipment |
| `repeated_resource_occurrence_count` | Sum of `max(usage_count - 1, 0)` over resources |
| `resource_reuse_ratio` | `shared_resource_count / unique_resource_count` (reported, not scored) |
| `resource_reuse_depth` | Repeated occurrences divided by `unique_resource_count * (group_size - 1)` |
| `compression` | `1 - unique_resource_count / resource_occurrence_count` |
| `shared_quantity_ratio` | Quantity belonging to shared IDs divided by all non-excluded quantity |
| `set_free_count` | Number of group members with no panoplie |
| `set_free_ratio` | `set_free_count / group_size` |
| `largest_set_share` | Members from the largest single panoplie, divided by `group_size` |
| `mean_pairwise_jaccard` | Mean recipe-set Jaccard over every equipment pair |
| `minimum_pairwise_jaccard` | Lowest pairwise Jaccard, or zero without a pair |
| `overlapping_pair_ratio` | Fraction of equipment pairs with positive Jaccard |
| `quality_score` | Configured weighted score defined below |

With default normalized weights:

```text
quality_score = clip(
    0.60 * compression
  + 0.20 * shared_quantity_ratio
  + 0.20 * set_free_ratio
  - 0.45 * largest_set_share,
    0,
    1,
)
```

`resource_reuse_ratio` carries a weight of `0.0` and is normalized out of the
reward sum, so it no longer contributes to the score; it is still computed and
reported. The three non-zero rewards are normalized together
(`0.45 / 0.60 = 0.60`, `0.15 / 0.60 = 0.20`, `0.15 / 0.60 = 0.20`), and the
set-concentration penalty is applied afterward without normalization.

The `k=5` panoplie exclusion removes large sets from the pool, but smaller
panoplies (2–4 members present) survive, so groups still contain set items.
Measured over the 179 default greedy groups: 94 have `set_free_ratio == 1.0`
and 85 have a non-zero `largest_set_share`; the median `set_free_ratio` is
`1.0` and the median `largest_set_share` is `0.0`, with median `compression`
`0.5`, median `shared_quantity_ratio` `0.8316`, and median `quality_score`
`0.5725`.

## Canonical Group Schema

All experts ultimately produce the following common fields:

```python
{
    "equipments": list[Equipment],
    "shared_resources_count": int,
    "total_shared_resources": set[int],
    "sharing_efficiency": float,
    "average_density": float,
    "break_density": dict[int, float],
    "items_per_line_item": float,
    "total_ingredients": dict[int, dict],
    "unique_ingredients_count": int,
    "total_items_needed": int,
    "group_size": int,
    "largest_set_share": float,
    "quality_metrics": dict[str, int | float],
    "quality_score": float,
}
```

`average_density` is the mean of `stat_weight / level` for equipment having a
positive level and a non-`None` weight. `break_density` contains the verified
per-item rune density from the valuation layer. `total_items_needed` is the sum of all
ingredient quantities. Each ingredient record contains its display name,
image URL when cached, total quantity, equipment names, quantities by name, and
quantities by equipment ID. Missing resource metadata falls back to
`"Resource <id>"`.

Expert metadata:

| Source | Additional fields |
| --- | --- |
| Deterministic | `selection_method="deterministic"`, `expert_name="GraphExpert"` |
| Random | `selection_method="random"`, `expert_name="RandomExpert"`, `seed_equipment_id`, `randomness_seed` |
| Greedy | `selection_method="greedy"`, `expert_name="GreedyExpert"` |
| Survey | `origins`/`origin` tagging the expert(s) that proposed the group |

`quality_metrics` contains every feature in the previous table, including a
second copy of `quality_score`. The top-level copy is the common expert ranking
field.

## Acceptance Policy

`GroupAcceptancePolicy` (`processing/policy.py`) is the single gate every expert
consults. `rejection_reason()` returns the first failed check, in this order:

1. `group_min_size <= size <= group_max_size` → `group_size`;
2. `shared_resources_count >= group_min_shared_resources` → `shared_resources_count`;
3. `sharing_efficiency >= group_efficiency_threshold`, **only when
   `group_size <= efficiency_threshold_max_size` (3)** → `sharing_efficiency`;
4. `quality_score >= group_quality_threshold` → `quality_score`;
5. `largest_set_share <= group_max_set_share` → `largest_set_share`;
6. `unique_ingredients_count <= max_line_items` → `max_line_items`;
7. `total_items_needed <= max_total_units` → `max_total_units`.

The efficiency floor is gated on small groups because `sharing_efficiency` only
discriminates there: at `group_size=2` it is exactly pairwise Jaccard, while
only 8.5% of 4-item groups fall below the floor. Gating keeps the check
meaningful without rejecting large cohesive groups.

`from_values(...)` builds a policy from explicit thresholds for the legacy
mapper entry points; it sets `max_set_share=1.0` and both shopping caps to
infinity, so those three checks are inert on that path.

## Deterministic Graph Expert

### Similarity Graph Path (`algorithm="louvain"` or fallback)

1. Build a bipartite equipment-resource graph. Node IDs are Ankama IDs and
   recipe quantities do not affect edges.
2. Extract each equipment's resource-ID set.
3. Use an inverted resource index to enumerate only equipment pairs sharing at
   least one resource.
4. Add a similarity edge only when both conditions pass:
   `Jaccard >= graph_min_shared_ratio` and
   `shared_count >= graph_min_shared_count`.
5. Store Jaccard as edge `weight` and the absolute count as `shared_count`.
6. Remove connected components smaller than `graph_min_component_size`.

Equipment and resource nodes use raw Ankama IDs in one NetworkX namespace. The
implementation therefore assumes those IDs do not collide across node types.

For `algorithm="louvain"`, each value in `resolution_range` produces a Louvain
partition. The selected partition maximizes the unweighted mean of community
mean pairwise recipe Jaccard; singleton communities do not contribute. When
`random_seed` is set it is passed as Louvain's `random_state`.

For any algorithm value other than `louvain` or `bilouvain`, connected
components become communities directly.

### BiLouvain Path (`algorithm="bilouvain"`)

BiLouvain bypasses the Jaccard similarity graph and its ratio, count, and
component thresholds. It builds the raw bipartite graph, projects it to an
equipment graph weighted by shared neighbors, and runs the same Louvain
resolution search. Resource nodes are assigned to neighboring communities
internally, then removed before group mapping. This is a weighted projection
approach, not a dedicated bipartite-modularity optimizer.

### Community Mapping

With `use_inclusive_mapping=False`, each community is one candidate. Communities
larger than `policy.max_size` are split first (see below); otherwise the
community is accepted only if `GroupAcceptancePolicy.accepts()` returns true.
Accepted groups are sorted by `quality_score` descending.

With `use_inclusive_mapping=True`, communities below `group_min_size` are
rejected and oversized communities are split by the same routine; each chunk is
then checked by the same policy. This path is currently unreachable:
`config.use_inclusive_mapping` defaults to `False` and nothing sets it `True`.

`_split_large_community()` packs resource-cohesive subgroups greedily, seeding
each chunk from the member with the highest remaining resource degree. An
earlier contiguous-slice implementation was removed: Louvain returns community
members in arbitrary order, so consecutive items frequently shared no resources
and every chunk failed the policy (probe R1 measured 100% loss on an 869-item
community split at `max_size=8`).

## Random Expert

Random search uses a process-local `random.Random` instance seeded
from `random_seed`; it does not mutate Python's module-level random state.

1. Use the pool exactly as supplied. The expert does not filter by density —
   `active_pool = equipments` (`processing/experts/random_expert.py`).
2. Build an inverted resource index for the active pool.
3. Perform at most `random_group_count` generation attempts.

For each attempt, the builder randomly selects a seed not previously used by a
successful group. Companion candidates must share at least
`group_min_shared_resources` non-excluded resources with the seed. Candidates
are ranked by the injected objective's marginal value for adding each candidate
to the seed group; the first `group_max_size - 1` are added. Without an
injected objective, the legacy shared-count ordering is retained for direct
builder compatibility.

A seed without a companion produces no group and still consumes one generation
attempt. Its ID is not marked used, so it may be selected again later. Every
successful group has a distinct seed. The requested count is therefore a target
and the result may contain fewer groups.

The builder rejects groups smaller than two. The expert then applies the common
acceptance policy. It does not de-duplicate overlapping equipment across groups.
`graph_min_shared_ratio`, `graph_min_shared_count`, and
`graph_min_component_size` do not affect standalone random grouping.

## Greedy Expert

The graph experts can only propose communities of the resource-similarity
graph, so items below the shared-resource threshold are never grouped at all.
The greedy expert grows groups directly against the objective instead, which
reaches items the graph discards. It is the default method.

1. Build a neighbour index from `recipe_resource_ids(e) - excluded_resource_ids`
   for the whole pool. It is independent of the similarity graph.
2. Order seeds by `break_density` descending (optionally truncated to
   `greedy_seed_limit`).
3. Skip a seed already covered, or one whose resource set is empty.
4. Grow from the seed: repeatedly shortlist the candidates sharing the most
   resources with the pooled set (capped at `greedy_candidate_limit`), score each
   via `objective.score(candidate.with_item(item))`, and add the best-scoring
   item while its score strictly exceeds the current score. Stop at
   `group_max_size` or when nothing improves the score.
5. Reject an item that would push one panoplie past `group_max_set_share`.
6. Drop the group when it is smaller than `group_min_size`; drop it when its
   fingerprint was already seen; drop it when the acceptance policy rejects it.
7. Mark accepted members as covered, so groups stay disjoint.

Groups are kept disjoint because the portfolio evaluator penalises duplicate
assignments, so an overlapping proposal scores worse than a small clean one.

The acceptance policy is the binding constraint, not reachability. On snapshot
3.7.7.6 the greedy expert grows 179 accepted groups and leaves 958 items
uncovered, but only 1 of those is truly isolated and only 2 have an empty
recipe; 949 still have a free partner. 796 grown groups are discarded by the
policy — 733 on `max_line_items`, 53 on `max_total_units`, and 10 on
`shared_resources_count`.

## Survey Method

`run_survey()` is diagnostic, not a production method. It builds one shared
graph, runs all three experts, and merges proposals by **exact equipment
fingerprint** (`frozenset` of `ankama_id`), tagging each surviving group with the
list of experts that proposed it (`origins`, plus a joined `origin` string). It
performs no Jaccard-based near-duplicate merging — `dedup_overlap_threshold` is
inert. The result is the union of all experts, sorted by `quality_score`
descending, so its coverage is an upper bound rather than a method result.

## Portfolio Evaluation And Summary

`PortfolioQualityEvaluator` evaluates the complete result after group creation.
Let assignments count an equipment once per group and unique equipment count it
once across the portfolio:

| Raw portfolio field | Meaning |
| --- | --- |
| `group_count` | Number of proposed groups |
| `total_assignments` | Sum of distinct equipment IDs within each group |
| `unique_equipment_count` | Distinct equipment IDs across all groups |
| `duplicate_assignment_count` | Assignments beyond the first portfolio occurrence |
| `equipment_coverage_rate` | Unique equipment divided by input equipment count |
| `assignment_overlap_rate` | Duplicate assignments divided by total assignments |
| `mean_group_quality` | Unweighted mean of group `quality_score` values |
| `assignment_weighted_group_quality` | Group quality weighted by each group's size |
| `mean_group_overlap` | Mean equipment-set Jaccard over group pairs |
| `maximum_group_overlap` | Maximum equipment-set Jaccard over group pairs |
| `portfolio_quality_score` | Configured reward-minus-overlap score clipped to `[0, 1]` |

```text
duplicate_assignment_count = total_assignments - unique_equipment_count
equipment_coverage_rate = unique_equipment_count / input_equipment_count
assignment_overlap_rate = duplicate_assignment_count / total_assignments
```

`assignment_weighted_group_quality` weights each group's `quality_score` by its
group size. `mean_group_overlap` and `maximum_group_overlap` are equipment-set
Jaccard values over every unordered pair of groups; both are zero with fewer
than two groups.

With the default portfolio weights:

```text
portfolio_quality_score = clip(
    0.65 * assignment_weighted_group_quality
  + 0.35 * equipment_coverage_rate
  - 0.50 * assignment_overlap_rate,
    0,
    1,
)
```

The first two weights are normalized together before use. The overlap penalty
is applied afterward without normalization.

`RuneMaster.get_summary()` returns `{}` when there are no groups. Otherwise it
returns:

```python
{
    "total_groups": int,
    "total_equipment_in_groups": int,  # assignment count, including repeats
    "unique_equipment_in_groups": int,
    "total_equipment": int,
    "retention_rate": float,  # compatibility alias of equipment_coverage_rate
    "equipment_coverage_rate": float,
    "duplicate_assignment_count": int,
    "assignment_overlap_rate": float,
    "average_efficiency": float,
    "average_quality_score": float,
    "assignment_weighted_quality_score": float,
    "mean_group_overlap": float,
    "maximum_group_overlap": float,
    "portfolio_quality_score": float,
    "max_efficiency": float,
    "min_efficiency": float,
    "average_group_size": float,
    "max_group_size": int,
}
```

## Measured Coverage

Measured on snapshot 3.7.7.6 (2858 equipment, 1642 resources, 3646 set
mappings; 2364 items after the `k=5` panoplie exclusion). `coverage` is
`covered / 2364`. All runs use `ProcessingConfig()` defaults except the field
named, and were executed through the shipped experts.

**Only `greedy` is reproducible without a seed.** The graph expert's Louvain
partition and the random expert both read `random_seed`, whose default is
`None`; with `random_seed=None` their results differ on every run (measured:
`deterministic` produced 97 and 109 groups on two consecutive runs, `random`
16 and 8, `survey` 285 and 288). The table below therefore pins
`random_seed=0` for the seeded methods. Greedy is seed-independent — it is
identical under `None` and `0`.

| Configuration | Groups | Covered | Coverage |
| --- | ---: | ---: | ---: |
| `greedy` (default, any seed) | 179 | 1406 | 59.48% |
| `deterministic`, `random_seed=0` | 97 | 1118 | 47.29% |
| `random`, `random_seed=0` | 11 | 52 | 2.20% |
| `survey`, `random_seed=0` (union of experts) | 287 | 1561 | 66.03% |

Any published per-method number for `deterministic`, `random`, or `survey` is
only meaningful with its seed stated. Greedy coverage levers, one field changed
at a time:

| Change | Groups | Covered | Coverage |
| --- | ---: | ---: | ---: |
| baseline | 179 | 1406 | 59.48% |
| `max_line_items=10000` | 217 | 1881 | 79.57% |
| `max_total_units=10**9` | 188 | 1478 | 62.52% |
| both shopping caps lifted | 241 | 2128 | 90.02% |
| `group_min_size=1` | 179 | 1406 | 59.48% |
| `group_max_size=24` + `max_line_items` lifted | 174 | 1880 | 79.53% |
| `greedy_candidate_limit=200` | 159 | 1315 | 55.63% |

The shopping budget — not singleton handling — sets coverage. `group_min_size=1`
changes coverage by exactly 0.00pp, because the growth loop only yields a
singleton where it had no admissible partner. `greedy_candidate_limit=200` is
worse than the default 25: a wider shortlist lets a seed consume items that
another seed would have grouped better.

`scripts/challenge_coverage_gap.py` reproduces the gap attribution and asserts
that coverage cannot exceed the pool size.

## Comparison Harness And Objective Seam

`processing.tools.harness.run_comparison()` runs the named production methods
offline, returning group-size, line-item, score, portfolio, and runtime columns
suitable for JSON persistence. Its `METHODS` tuple is
`("deterministic", "random", "greedy")`.

The objective seam is `processing/valuation/objective.py`: `GroupCandidate` is an
immutable group plus its excluded resources, and `GroupObjective` is the
protocol with `score()` and a default `marginal()`
(`score(with_item) - score`). No objective overrides `marginal()`.
`OverlapObjective` wraps `GroupQualityEvaluator` and is the only objective wired
into the experts. Two call styles are in use: the greedy expert scores
`objective.score(candidate.with_item(item))` directly, while
`RandomGroupBuilder.find_companions()` ranks candidates with
`objective.marginal(seed_group, item)` when an objective is injected.

`ProfitObjective` reports theoretical values in kamas, records each selected
focus, excludes partially priced items from the profit term, and falls back
explicitly to the compression overlap score when no item can be valued. It is
not active: it requires a `PriceSource`, and the default `NullPriceSource`
returns no prices.

`break_log` is append-only user data, separate from cache invalidation. Use
`python break_log.py` for manual observations; each row stores UTC time, source,
runes received, and observed density so taux can be computed later.

`PosteriorTauxModel` uses explicit half-life and planned-volume decay constants.
It reports confidence and an exploration bonus; unseen items use the prior and
are never treated as zero-value.

`processing.valuation.exploration.rank_exploration()` ranks items by theoretical density
per recipe unit, expected taux, and exploration bonus. The HTML generator and
`exploration_shortlist.py` expose the same candidates, including a direct
manual-record command.

## Parameter Tuning

`ParameterTuner` evaluates the Cartesian product:

- `graph_min_shared_ratio`: `0.15`, `0.20`, `0.25`, `0.30`;
- `group_min_shared_resources`: `2`, `3`, `4`.

Each of the 12 configurations runs in a separate process with its own cache
manager and a newly constructed config. Worker configs use processing defaults
except for the two searched fields, the requested method,
`use_density_filtering=True`,
`equipment_density_level_ratio=1.5`, and `random_seed=0`.

The objective is `portfolio_quality_score`; no groups means score zero. Ties are
resolved by completion order because the best result changes only on a strictly
higher score.

Parameter relevance depends on the method:

| Method passed to tuner | Ratio relevant? | Shared-count relevant? | Worker dispatch |
| --- | --- | --- | --- |
| `deterministic` | Yes | Yes | Deterministic with default Louvain |
| `random` | No | Yes, for companions and final filtering | Random |
| `greedy` | Yes | Yes | Greedy |
| Any other value | Yes | Yes | `run_all()`, therefore deterministic with default Louvain |

The tuner does not search or copy the caller's algorithm, quality weights,
group sizes, density settings, resolution, seed, or overlap threshold into its
workers. Workers therefore always evaluate default Louvain. During CLI tuning,
only the winning ratio and shared-count values are copied onto the caller's
original config; the final run preserves the caller's other settings. Returned
tuner statistics describe the worker config, not that merged final config.

This is reproducible heuristic grid search, not model training or statistical
validation. For random grouping, every ratio candidate is behaviorally
irrelevant and therefore repeats equivalent work. The tuner's
`use_density_filtering` / `equipment_density_level_ratio` arguments are inert
for the same reason they are inert everywhere else.

## Reproducibility

- Louvain receives `random_seed` as `random_state`.
- The random expert uses a process-local `random.Random` instance seeded from
  `random_seed`; it does not mutate Python's module-level random state.
- Tuner workers always override the seed to `0`.
- `random_seed=None` leaves stochastic paths unseeded.
- API data, input ordering, library versions, and cache metadata are not part of
  the seed and must be captured separately for a reproducible run manifest.
- The snapshot loader keeps equipment whose `stat_weight` is zero or negative,
  while the live loader (`EquipmentLoader.from_raw_batch`) drops it. On snapshot
  3.7.7.6 that is 86 items, so a snapshot run and a live run do not see the same
  population.

## Architecture And Ownership

```text
processing/
|-- __init__.py            Package docstring and public re-exports
|-- orchestrator.py        RuneMaster MoE coordinator and method dispatch
|-- config.py              ProcessingConfig and defaults
|-- policy.py              GroupAcceptancePolicy (single acceptance gate)
|-- graph/
|   |-- graph_builder.py        Bipartite and Jaccard similarity graphs
|   |-- community_detector.py   Resolution search and community conversion
|   `-- group_mapper.py         Community filtering and optional splitting
|-- experts/
|   |-- base.py                 GroupingExpert ABC (the interface for all experts)
|   |-- graph_expert.py         Deterministic graph/community path
|   |-- random_expert.py        Random path (no density filtering)
|   |-- random_group_builder.py Seed-and-companion proposal construction
|   `-- greedy_expert.py        Objective-driven greedy growth
|-- filters/
|   |-- equipment_filter.py     Panoplie set exclusion; density filtering (unused at runtime)
|   `-- job_filter.py           Craftability filtering by player job levels
|-- metrics/
|   |-- quality_metrics.py      Item-only and portfolio feature evaluation
|   |-- group_metrics.py        Canonical group dictionary and legacy metrics
|   |-- break_log.py            Observed-taux and rune-density helpers
|   `-- selection.py            ProcessingReporter (run summary)
|-- valuation/
|   |-- objective.py            GroupCandidate and GroupObjective protocol
|   |-- overlap.py              OverlapObjective (the active objective)
|   |-- economic.py             ProfitObjective and FlatTauxModel
|   |-- focus.py                Break-density and focus formulas
|   |-- density.py              RUNE_DENSITY table and stat-name resolution
|   |-- taux.py                 PosteriorTauxModel
|   |-- prices.py               PriceSource contracts
|   |-- exploration.py          Break-exploration ranking
|   `-- stat_calculator.py      Stat-weight calculation used by data loaders
|-- blocks/
|   |-- recipes.py              Recipe normalization helpers
|   |-- shopping_list.py        Shopping-list arithmetic
|   `-- similarity.py           Jaccard similarity
`-- tools/
    |-- harness.py              Offline method comparison
    `-- tuner.py                Parallel heuristic grid search
```

`api_client` is retained in several signatures for compatibility but is not
used to create groups. Resource names and images come from `cache_manager` when
available.

Analysis-only code lives outside this package: `analysis/challenge_metrics.py`
implements the API-only challenge metrics (M1–M9) and is never imported by the
runtime pipeline.

## Known Behavioral Constraints

- Recipe overlap is not economic value. Prices and rune outcomes are absent.
- `sharing_efficiency` has legacy exclusion semantics different from the new
  quality features; do not treat the two ratios as interchangeable.
- The acceptance policy's shopping caps, not reachability, bound greedy
  coverage. Relaxing them raises coverage but also raises shopping effort.
- Random grouping is seed-centric and can create groups whose companions do not
  share resources with one another.
- The `use_inclusive_mapping` split path is unreachable with shipped defaults.
- Survey de-duplication is by exact equipment fingerprint; there is no
  near-duplicate merging, and `dedup_overlap_threshold` is not consulted.
- `EquipmentFilteringStrategy` and its config fields are inert at runtime.
- Snapshot and live loading disagree on zero-`stat_weight` equipment.
- `processing/valuation/density.py` owns the game's `RUNE_DENSITY` table; the
  calculator uses it to populate equipment stat weights.

## Executable Contracts

The offline tests that protect this specification are:

- `test/test_quality_metrics.py`: feature boundaries, exclusions, quantity
  sensitivity, portfolio overlap, random threshold parity, and BiLouvain;
- `test/test_pipeline_contracts.py`: deterministic, random, summary,
  and report integration contracts;
- `test/test_group_structure.py`: canonical group and ingredient schema;
- `test/test_policy.py` and `test/test_metrics_revision.py`: acceptance-policy
  ordering, the small-group efficiency gate, and the score-term set;
- `test/test_refactor_snapshot.py`: locked deterministic and random outputs plus
  the density-filter fallback paths (which exercise the inert strategy directly).

Validation gate:

```bash
uv run pytest -q
python3 -m compileall -q data processing analysis main.py config.py test visualization scripts
git diff --check
```
