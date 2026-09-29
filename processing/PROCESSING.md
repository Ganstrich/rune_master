# Processing Module

This document is the authoritative functional specification for group creation
in RuneMaster. It describes the behavior implemented under `processing/` and
the dispatch performed by `main.py`. A change to group construction, filtering,
scoring, selection, or configuration is incomplete until this file and its
contract tests are updated in the same change.

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

`data.loaders` calculates stat weights and may apply
`min_equipment_density` before this module is called. Within `processing/`, only
the random expert applies density filtering. Deterministic and genetic grouping
use the complete equipment list passed to `RuneMaster`.

## End-To-End Dispatch

`main.py::process_equipment()` constructs `RuneMaster` and dispatches from
`ProcessingConfig.grouping_method`:

| Value | Method called | Result |
| --- | --- | --- |
| `deterministic` | `run_all()` | Graph expert only; `run_all()` is a backward-compatible alias for `run_deterministic()` |
| `random` | `run_random_grouping()` | Random expert only |
| `hybrid` | `run_hybrid_grouping()` | Graph expert, optionally supplemented by random groups |
| `committee` | `run_committee()` | Greedy ensemble of graph, random, and genetic proposals |
| `genetic` | `run_genetic_grouping()` | Genetic expert only |

The CLI restricts the value to those five choices. Calling `run_all()` directly
does not inspect `grouping_method`; it always runs deterministic grouping.

Every accepted proposal is a canonical group dictionary built by
`GroupMetrics.build_group_dict()`. Expert-specific metadata is added afterward.

## Configuration

`ProcessingConfig` is the runtime configuration contract.

| Field | Default | Applies to | Exact behavior |
| --- | ---: | --- | --- |
| `graph_min_shared_ratio` | `0.3` | Jaccard graph paths; not BiLouvain | Minimum pairwise recipe Jaccard for a similarity edge |
| `graph_min_shared_count` | `1` | Jaccard graph paths; not BiLouvain | Minimum absolute shared resource IDs for the same edge; both edge conditions must pass |
| `graph_min_component_size` | `2` | Jaccard graph paths; not BiLouvain | Connected components smaller than this are removed |
| `algorithm` | `louvain` | Graph expert | `louvain`, `bilouvain`, or any other value for connected components |
| `resolution_range` | `(1, 10, 1)` | Louvain and BiLouvain | Passed to `np.arange(start, stop, step)`; the stop value is excluded |
| `group_min_size` | `2` | All experts | Minimum accepted group size, except the documented inclusive-split edge case |
| `group_max_size` | `32` | All experts | Generous upper bound; shopping-list caps are primary |
| `group_min_shared_resources` | `3` | All experts | Minimum number of non-excluded resource IDs used by at least two items |
| `group_efficiency_threshold` | `0.15` | All experts | Minimum legacy `sharing_efficiency` |
| `group_quality_threshold` | `0.0` | All experts | Minimum item-only `quality_score` |
| `max_line_items` | `12` | Acceptance policy | Maximum distinct resources in the shopping list |
| `max_total_units` | `500` | Acceptance policy | Maximum total recipe units in the shopping list |
| `acquisition_cost` | `0.0` | Profit objective | Kama-equivalent fixed cost per distinct resource |
| `flat_taux` | `1.0` | Profit objective | Theoretical constant until break outcomes are logged |
| `price_max_age_seconds` | `3600.0` | Price source | Maximum age for a usable cached price |
| `group_quality_weights` | `0.50/0.30/0.20` | Canonical group evaluator | Weights for compression, reuse, and shared quantity |
| `use_inclusive_mapping` | `False` | Graph expert | Split oversized communities instead of rejecting them whole |
| `excluded_resource_ids` | `{15263, 14635}` | Group filters, quality, random/genetic affinity | Resource IDs ignored where explicitly described below |
| `density_percentile` | `0.0` | Loader pool | Within-level-band stat-density percentile; zero disables filtering |
| `density_level_band` | `20` | Loader pool | Level width used for percentile filtering |
| `grouping_method` | `hybrid` | `main.py` dispatch | Selects the orchestrator path; `RuneMaster.run_all()` ignores it |
| `random_group_count` | `50` | Random and hybrid | Maximum number of random generation attempts and hybrid threshold input |
| `random_seed` | `None` | Louvain, random, genetic | Seeds the corresponding stochastic operations when set |
| `min_equipment_density` | `0.0` | Loader only | Absolute minimum `stat_weight`, despite the historical field name |
| `dedup_overlap_threshold` | `0.7` | Committee only | Equipment-set Jaccard at or above this value rejects a later proposal |
| `portfolio_quality_weights` | `0.65/0.35/0.50` | Summary and tuner | Group-quality reward, coverage reward, and overlap penalty |

The reward fields in both weight dataclasses must be non-negative. Group-quality
weights are normalized to sum to one. Portfolio group-quality and coverage
weights are normalized together; the overlap penalty is not normalized.

## Recipe And Resource Semantics

For set-based calculations, a resource can occur at most once per equipment,
even if malformed input repeats it in that recipe. Across a group:

- a resource is **shared** when it appears in at least two equipment recipes;
- recipe Jaccard is `|resources_a intersection resources_b| / |union|`;
- graph construction ignores recipe quantities;
- ingredient aggregation sums recipe quantities.

There are two intentionally distinct resource metrics:

Exclusions are not applied uniformly during candidate discovery. The Jaccard
similarity graph and BiLouvain projection include every recipe resource,
including configured exclusions. The random expert removes exclusions before
seed-companion matching. The genetic expert's graph includes them, while its
conflict-affinity resource sets remove them. Final group filters and item-only
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
| `resource_reuse_ratio` | `shared_resource_count / unique_resource_count` |
| `resource_reuse_depth` | Repeated occurrences divided by `unique_resource_count * (group_size - 1)` |
| `compression` | `1 - unique_resource_count / resource_occurrence_count` |
| `shared_quantity_ratio` | Quantity belonging to shared IDs divided by all non-excluded quantity |
| `mean_pairwise_jaccard` | Mean recipe-set Jaccard over every equipment pair |
| `minimum_pairwise_jaccard` | Lowest pairwise Jaccard, or zero without a pair |
| `overlapping_pair_ratio` | Fraction of equipment pairs with positive Jaccard |
| `quality_score` | Configured weighted score defined below |

Pairwise Jaccard and overlap remain diagnostics, but are not scored. With
default normalized weights:

```text
quality_score = 0.50 * compression
              + 0.30 * resource_reuse_ratio
              + 0.20 * shared_quantity_ratio
```

Identical two-item non-empty recipes score `0.75`; disjoint recipes score
`0.0`. The score is a heuristic shortlist target, not observed
utility, profit, savings, or a trained prediction.

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

Genetic groups additionally include `provenance`, set to `evolved` for
warm-started re-evaluation and `newly_discovered` for cold-start search.

| Source | Additional fields |
| --- | --- |
| Deterministic | `selection_method="deterministic"`, `expert_name="GraphExpert"` |
| Random | `selection_method="random"`, `expert_name="RandomExpert"`, `seed_equipment_id`, `randomness_seed` |
| Genetic | `selection_method="genetic"`, `expert_name="GeneticExpert"` |
| Committee-selected proposal | Existing expert fields plus `fitness_score` |

`quality_metrics` contains every feature in the previous table, including a
second copy of `quality_score`. The top-level copy is the common expert ranking
field.

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

With `use_inclusive_mapping=False`, each community is one candidate. It is
accepted only if the shared `GroupAcceptancePolicy` accepts it, with these
checks evaluated in order:

1. `group_min_size <= size <= group_max_size`;
2. `shared_resources_count >= group_min_shared_resources`;
3. `sharing_efficiency >= group_efficiency_threshold`;
4. `quality_score >= group_quality_threshold`.

Oversized communities are rejected whole.

With `use_inclusive_mapping=True`, communities below `group_min_size` are
rejected. Oversized communities are split into sequential list chunks of
`group_max_size`; splitting is not graph-aware or re-optimized. Each chunk is
then checked by the same policy. The policy applies the minimum-size check to
each chunk as well as shared-resource count, legacy efficiency, and quality.

Accepted groups are sorted by `quality_score` descending.

## Random Expert

Random and genetic searches use process-local `random.Random` instances seeded
from `random_seed`; they do not mutate Python's module-level random state.

1. If density filtering is disabled, use the complete input pool.
2. Otherwise retain equipment satisfying
   `stat_weight >= level * equipment_density_level_ratio`. Equipment with a
   `None` weight is excluded.
3. If the filtered pool is smaller than `min_filtered_pool_size` and
   `fallback_to_unfiltered=True`, use the original pool. Otherwise keep the
   filtered pool, even when it is empty or small.
4. Build an inverted resource index for the active pool.
5. Perform at most `random_group_count` generation attempts.

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
minimum size, maximum size, shared-resource, legacy-efficiency, and quality
thresholds. It does not de-duplicate overlapping equipment across groups.
`graph_min_shared_ratio`, `graph_min_shared_count`, and
`graph_min_component_size` do not affect standalone random grouping.

## Baseline And Comparison Harness

`BaselineExpert` ranks items by break density and greedily packs them using the
injected objective. `processing.harness.run_comparison()` runs the baseline and
all named production methods offline, returning group-size, line-item, score,
portfolio, and runtime columns suitable for JSON persistence.

`ProfitObjective` reports theoretical values in kamas, records each selected
focus, excludes partially priced items from the profit term, and falls back
explicitly to the compression overlap score when no item can be valued.

`break_log` is append-only user data, separate from cache invalidation. Use
`python break_log.py` for manual observations; each row stores UTC time, source,
runes received, and observed density so taux can be computed later.

`PosteriorTauxModel` uses explicit half-life and planned-volume decay constants.
It reports confidence and an exploration bonus; unseen items use the prior and
are never treated as zero-value.

`processing.exploration.rank_exploration()` ranks items by theoretical density
per recipe unit, expected taux, and exploration bonus. The HTML generator and
`exploration_shortlist.py` expose the same candidates, including a direct
manual-record command.

## Genetic Expert

The genetic expert first builds or reuses the same filtered Jaccard similarity
graph used by the graph expert. An empty graph returns no groups. Excluded
resource IDs are removed from resource sets used for conflict affinity.

Default search parameters, now configurable through `ProcessingConfig`, are:

| Parameter | Default |
| --- | ---: |
| Population size | `30` |
| Maximum generations | `50` |
| Mutation rate | `0.3` |
| Elite count | `3` |
| Stagnation limit | `15` |

An individual is a list of non-overlapping equipment sets:

1. Initialization targets between three and eight groups.
2. Each group starts from a random surviving graph node and repeatedly adds an
   available neighbor with maximum summed edge weight to current members.
3. Target group size is sampled between configured minimum and maximum, but
   growth stops early when no available neighbor remains.
4. Equipment assigned to one initial group is removed from that individual's
   available set.

If growth stops below `group_min_size`, the candidate is not appended, but its
nodes have already been removed from that individual's available set. Crossover
conflict resolution may also leave empty or undersized sets; they remain in the
individual but contribute zero fitness and cannot survive final filtering.

Individual fitness is the sum of qualifying group `quality_score` values minus
`1.0` for every duplicate equipment assignment. Groups outside size limits or
below shared-resource, legacy-efficiency, or quality thresholds contribute
zero. The overlap penalty is defensive because initialization, crossover
conflict resolution, and mutation normally maintain unique assignments.

Each generation:

1. carries the `elite_count` highest-fitness individuals unchanged;
2. selects parents by three-candidate tournament selection;
3. pools parent groups and randomly sends each group to child one, child two,
   or both;
4. resolves duplicate equipment within a child by retaining it in the group
   with greatest resource-set affinity;
5. independently mutates each child with `mutation_rate` probability.

Mutation chooses one operation:

- `add`: add an unassigned graph neighbor when the group is below maximum size;
- `remove`: remove one equipment when the group is above minimum size;
- `merge`: merge two groups when the union does not exceed maximum size.

Evolution stops after `generations` or after `stagnation_limit` consecutive
generations without a strictly better best fitness. Final groups come from the
best individual ever seen and are rebuilt canonically, then all common
constraints are applied again. The final list is not explicitly sorted.

When `random_seed` is set, the expert seeds Python's module-level random
generator before initialization.

## Hybrid Method

Hybrid always runs the graph expert first. It calculates:

```text
supplement_threshold = max(5, int(random_group_count * 0.5))
```

If the deterministic result count is below that threshold, hybrid runs the
random expert and concatenates `deterministic_groups + random_groups`.
Otherwise it returns deterministic groups only. Hybrid performs no cross-source
sorting or de-duplication, so equipment and near-identical groups may repeat.

## Committee Method

Committee is a greedy proposal ensemble, not a learned gating network:

1. Build the configured Jaccard similarity graph once.
2. Invoke graph, random, and genetic experts in that order, passing the shared
   graph and resource map. The graph expert rebuilds a bipartite graph instead
   when `algorithm="bilouvain"`; the random expert ignores the shared graph.
3. Catch `IndexError`, `KeyError`, `RuntimeError`, `TypeError`, or `ValueError`
   from each expert. Record the failure and continue with remaining experts.
4. Set each proposal's `fitness_score` using its expert's evaluator. All current
   experts use top-level `quality_score`.
5. Sort all proposals by fitness descending. Python's stable sort preserves
   expert production order for exact ties.
6. Greedily scan proposals. Reject groups smaller than two. Reject a proposal
   when its equipment-set Jaccard with any already accepted group is greater
   than or equal to `dedup_overlap_threshold`; otherwise accept it.

The committee does not optimize the portfolio score during selection and does
not impose a maximum number of final groups. `get_expert_report()` returns
recorded failures and the selected-group count.

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

## Parameter Tuning

`ParameterTuner` evaluates the Cartesian product:

- `graph_min_shared_ratio`: `0.15`, `0.20`, `0.25`, `0.30`;
- `group_min_shared_resources`: `2`, `3`, `4`.

Each of the 12 configurations runs in a separate process with its own cache
manager and a newly constructed config. Worker configs use processing defaults
except for the two searched fields, requested method,
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
| `committee` | Yes for graph/genetic; no for random | Yes | Committee with default Louvain |
| `genetic` | Yes | Yes | Genetic |
| Any other value, including `hybrid` | Yes | Yes | `run_all()`, therefore deterministic with default Louvain |

The tuner does not search or copy the caller's algorithm, quality weights,
group sizes, density settings, resolution, seed, or overlap threshold into its
workers. Workers therefore always evaluate default Louvain. During CLI tuning,
only the winning ratio and shared-count values are copied onto the caller's
original config; the final run preserves the caller's other settings. Returned
tuner statistics describe the worker config, not that merged final config.

This is reproducible heuristic grid search, not model training or statistical
validation. For random grouping, every ratio candidate is behaviorally
irrelevant and therefore repeats equivalent work.

## Reproducibility

- Louvain receives `random_seed` as `random_state`.
- Random and genetic experts seed Python's module-level random generator.
- Tuner workers always override the seed to `0`.
- `random_seed=None` leaves stochastic paths unseeded.
- Random and genetic use the same process-level generator. A configured seed is
   applied again when each expert starts; with `None`, earlier stochastic work
   can affect later expert state in hybrid or committee execution.
- API data, input ordering, library versions, and cache metadata are not part of
  the seed and must be captured separately for a reproducible run manifest.

## Architecture And Ownership

```text
processing/
|-- config_dataclass.py       ProcessingConfig and defaults
|-- graph_builder.py          Bipartite and Jaccard similarity graphs
|-- community_detector.py     Resolution search and community conversion
|-- group_mapper.py           Community filtering and optional splitting
|-- group_metrics.py          Canonical group dictionary and legacy metrics
|-- quality_metrics.py        Item-only and portfolio feature evaluation
|-- equipment_filter.py       Random-pool density filtering
|-- random_group_builder.py   Seed-and-companion proposal construction
|-- orchestrator.py           Method dispatch, hybrid, committee, summaries
|-- tuner.py                  Parallel heuristic grid search
|-- stat_calculator.py        Stat-weight calculation used upstream by data loaders
|-- resource_optimizer.py     Empty placeholder; no runtime behavior
`-- experts/
    |-- base.py               Shared expert interface and default evaluator
    |-- graph_expert.py       Deterministic graph/community path
    |-- random_expert.py      Density-filtered random path
    `-- genetic_expert.py     Evolutionary path
```

`api_client` is retained in several signatures for compatibility but is not
used to create groups. Resource names and images come from `cache_manager` when
available.

## Known Behavioral Constraints

- Recipe overlap is not economic value. Prices and rune outcomes are absent.
- `sharing_efficiency` has legacy exclusion semantics different from the new
  quality features; do not treat the two ratios as interchangeable.
- Random grouping is seed-centric and can create groups whose companions do not
  share resources with one another.
- Inclusive splitting is sequential, not graph-aware.
- Hybrid concatenation can duplicate groups; committee de-duplication is greedy
  and pairwise rather than globally optimal.
- Committee selection ranks individual groups and only evaluates portfolio
  quality afterward.
- `processing/valuation/density.py` owns the game's `RUNE_DENSITY` table; the
   calculator retains a compatibility alias and uses it to populate equipment
   stat weights.
  filtering and reporting, not item-only recipe quality.

## Executable Contracts

The offline tests that protect this specification are:

- `test/test_quality_metrics.py`: feature boundaries, exclusions, quantity
  sensitivity, portfolio overlap, random threshold parity, and BiLouvain;
- `test/test_pipeline_contracts.py`: deterministic, random, hybrid, summary,
  and report integration contracts;
- `test/test_group_structure.py`: canonical group and ingredient schema.

Validation gate:

```bash
uv run pytest -q
python3 -m compileall -q data processing main.py config.py test visualization
git diff --check
```