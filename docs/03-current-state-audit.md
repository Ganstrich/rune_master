# Current State Audit

Findings from a read of `processing/` on 2026-09-29. Every claim is tagged
**[VERIFIED-CODE]** unless noted. Line references were accurate at time of
writing; re-confirm before acting.

[../processing/PROCESSING.md](../processing/PROCESSING.md) remains the
authoritative description of current behavior. This document records what is
*wrong* with that behavior relative to the objective in
[02-objective-model.md](02-objective-model.md).

## What Is Sound

Worth stating, because the problems below are about fitness for purpose, not
craftsmanship:

- The module dependency graph is **acyclic**, with no layering violations.
- `GroupMetrics.build_group_dict()` is a genuine single source of truth for the
  canonical group schema.
- The quality features are transparent, documented, and contract-tested.
- `STAT_WEIGHTS` is the rune density table — a correct and valuable asset that
  the code under-uses (see [01-domain-model.md](01-domain-model.md)).
- `PROCESSING.md` is unusually honest about its own limitations, including
  "Recipe overlap is not economic value."
- **Set membership tracking** (`equipment_sets`, `same_set_edge_discount`,
  `group_max_set_share`, `set_free_ratio`, `set_concentration_penalty`) is a
  valuable feature that is currently under-used. Set items are heavily broken
  by other players and have low taux — this is a prior on exploration value
  that the objective does not yet incorporate.

## The Structural Blocker: Experts Own The Definition Of Good

**This is the most important finding.** The intended design is *building blocks
produce candidates, experts assemble groups, an objective ranks them*. The code
violates this: each expert hardcodes its own notion of quality, so the objective
cannot be swapped.

| Site | What it hardcodes |
| --- | --- |
| [../processing/experts/genetic_expert.py](../processing/experts/genetic_expert.py) | Instantiates `GroupQualityEvaluator` inline; applies three thresholds itself |
| [../processing/experts/random_expert.py](../processing/experts/random_expert.py) | Re-applies the same thresholds after building |
| [../processing/experts/graph_expert.py](../processing/experts/graph_expert.py) | Delegates to `GroupMapper`, which applies them a third time |
| [../processing/random_group_builder.py](../processing/random_group_builder.py) | Embeds a *fourth*, different notion — shared-count-with-seed — in its companion sort |

`evaluate_group()` in
[../processing/experts/base.py](../processing/experts/base.py) exists to be the
objective seam but is an identity function returning `group["quality_score"]`,
called from exactly one place.

**Consequence:** switching from overlap to profit means editing four sites, and
the genetic expert's *search* — fitness, crossover affinity, mutation choice —
is wired to recipe overlap specifically. These experts cannot be re-pointed at a
new objective; they would be rewritten. Fixing this is a prerequisite for
everything in [05-roadmap.md](05-roadmap.md).

## Failing 1 — The Objective Decays With Group Size

The four weighted features in
[../processing/quality_metrics.py](../processing/quality_metrics.py) are all
intensive ratios in $[0,1]$. `group_size` and `unique_resource_count` are
computed but carry **weight zero**.

```python
resource_reuse_ratio: float = 0.30
mean_pairwise_jaccard: float = 0.30
overlapping_pair_ratio: float = 0.20
shared_quantity_ratio: float = 0.20
```

`mean_pairwise_jaccard` averages over all $\binom{n}{2}$ pairs; each added item
contributes $n$ new, typically weaker pairs, so the mean falls.
`overlapping_pair_ratio` behaves identically. `resource_reuse_ratio` is
shared/unique, and each added item inflates the denominator with resources
shared with nobody.

Two items with identical recipes score exactly **1.0**, the theoretical maximum.
Ten items sharing 8 of 12 resources — a far better production run — scores well
below it.

**Consequence:** the threshold gates acceptance and the committee ranks by this
same number, so the best-ranked outputs are systematically the smallest.
`group_max_size=18` never binds because nothing rewards approaching it. Four
search algorithms compete to find item *pairs*, which defeats the purpose stated
in [01-domain-model.md](01-domain-model.md): craft **many varied** items to
discover high-taux ones.

**Fix:** the compression term in
[02-objective-model.md](02-objective-model.md).

## Failing 2 — The Genetic Expert Amplifies That Bias And Uses A Divergent Filter

In `_calculate_individual_fitness`:

```python
if (
    quality.shared_resource_count < config.group_min_shared_resources
    or quality.resource_reuse_ratio < config.group_efficiency_threshold
    or quality.quality_score < config.group_quality_threshold
):
    continue
total_score += quality.quality_score
```

Four defects:

1. **Fitness is a sum of per-group scores.** Twelve mediocre pairs beat four
   excellent large groups, compounding Failing 1.
2. **It filters `resource_reuse_ratio` with `group_efficiency_threshold`**, but
   `GroupMapper` applies that same threshold to `sharing_efficiency`, a
   *different formula* — excluded resource IDs sit in its denominator but not
   its numerator. One config value, two meanings, two different accept sets.
3. **The docstring is stale**, claiming "Fitness = Sum(group_sharing_efficiency)"
   and "uses the canonical sharing_efficiency definition." It sums
   `quality_score`.
4. `resource_sets` is a declared parameter that is never read, and `config` is
   typed `Optional[...] = None` while the body dereferences it unguarded —
   passing `None` crashes rather than defaulting.

## Failing 3 — The Random Expert Builds Stars, Not Cliques

In `find_companions`
([../processing/random_group_builder.py](../processing/random_group_builder.py)):

```python
shared_count = len(seed_resources & eq_resources)
if shared_count >= min_shared_resources:
    efficiency = shared_count / len(seed_resources) if seed_resources else 0
    companions.append((eq, shared_count, efficiency))

companions.sort(key=lambda item: (item[1], item[2]), reverse=True)
```

Every candidate is compared **only to the seed**; companions are never compared
to each other. The result is a star: seed $s$ shares three resources with each
of $a$, $b$, $c$, while $a$, $b$, $c$ are mutually disjoint. The shopping list is
then roughly $|R_s| + \sum(|R_i| - 3)$ — linear in group size, the exact failure
mode the project exists to avoid. It passes every current filter.

Secondary defects: `efficiency` normalises by `len(seed_resources)` only, so
short-recipe seeds score inflated; the sort puts absolute `shared_count` first,
biasing toward large-recipe companions, which are the items that lengthen the
list most; and the local default `min_shared_resources: int = 2` disagrees with
`group_min_shared_resources: int = 3` in
[../processing/config_dataclass.py](../processing/config_dataclass.py).

**Fix:** companion selection should be greedy on *marginal* cost — pick the
candidate adding the fewest new line items — which is what a `marginal()`
objective method provides.

## Failing 4 — Constraints Bind On The Wrong Object

`group_min_size: int = 2` and `group_max_size: int = 18` cap **item count**.
Nothing constrains `unique_resource_count` or `total_items_needed`, both of
which are already computed and stored in the canonical group dict.

A 4-item group needing 40 distinct resources is accepted. A 20-item group
needing 9 is rejected for exceeding `group_max_size`. That is inverted relative
to the objective.

## Failing 5 — Portfolio Scoring Fights The Product

```python
group_quality: float = 0.65
equipment_coverage: float = 0.35
assignment_overlap_penalty: float = 0.50
```

The penalty applies to **equipment** overlap between groups, which is
defensible. But there is no treatment of **resource** overlap between groups,
and that is the one that matters: two groups needing the same resource is one
bulk purchase serving two runs — strictly good.
[../plans/04-combined-shopping-list.md](../plans/04-combined-shopping-list.md)
exists specifically to let users combine groups, so the scoring is blind to the
property that feature depends on.

Also, `normalized_rewards()` normalises only the two reward weights, so the 0.50
penalty sits on a different scale and is effectively stronger than it appears.

## Failing 6 — The Value Gate Covers One Of Five Paths

Density filtering (`stat_weight >= level * ratio`,
[../processing/equipment_filter.py](../processing/equipment_filter.py)) runs
**only** inside the random expert. `use_density_filtering=True` reads as global;
it is not.

So `deterministic`, `hybrid`, `genetic`, and `committee` can all emit groups
containing items that break into worthless runes. The default
`grouping_method` is `hybrid`. Secondary: the filter is linear in level while
stat budgets scale super-linearly, so it over-retains high-level items.

## Failing 7 — Two Gates Measure The Same Thing Incompatibly

`group_efficiency_threshold` filters `sharing_efficiency`, whose numerator
excludes `excluded_resource_ids` while its denominator includes them.
`group_quality_threshold` filters `quality_score`, whose `resource_reuse_ratio`
removes exclusions from both sides.

Excluded resources can therefore only ever *lower* `sharing_efficiency` — a
group is penalised by a gate meant to ignore those resources. The two gates are
correlated but not monotone in each other, so tuning one perturbs the other
unpredictably, and [../processing/tuner.py](../processing/tuner.py)
grid-searches a third correlated gate against an objective containing both.

## Smaller Defects

| Defect | Location |
| --- | --- |
| Jaccard implemented four times with four signatures | `quality_metrics.py` (twice), `orchestrator.py`, `graph_builder.py` |
| `calculate_bulk_efficiency` is dead **and wrong** — uses `set.intersection(*all)` (resources in *every* item) where the spec says "used by >= 2" | `community_detector.py` |
| `resource_optimizer.py` is empty; `use_resource_optimizer` is read by nothing | `resource_optimizer.py`, `config_dataclass.py` |
| `api_client` threaded through ~8 signatures, then `del`'d on arrival | `group_metrics.py` and callers |
| Global `random` module with `random.seed()`, unsafe under the tuner's `ProcessPoolExecutor` | `random_group_builder.py`, `genetic_expert.py` |
| `ProcessingConfig` imports `quality_metrics` — config depends on an algorithm module | `config_dataclass.py` |
| `stat_calculator.py` sits in `processing/` but its only consumer is `data/loaders.py`; it is a valuation concern | `stat_calculator.py` |
| "Committee" is a union-with-dedup, not a mixture of experts: no gating, no weighting, and all experts are ranked by the identical score | `orchestrator.py` |
| Tuner searches 2 parameters against a proxy-of-a-proxy, and discards the caller's algorithm, weights, and seed in workers, so results do not transfer | `tuner.py` |

## No External Validation Signal

`quality_score` is simultaneously: the thing algorithms maximise, the acceptance
threshold, the committee ranking key, and an input to
`portfolio_quality_score`, which is the tuner's objective. A score that grades
its own output cannot indicate whether grouping works.

Nothing is compared against a trivial baseline. Before adding more search
sophistication, implement one — for example, top-K items by value density,
greedily packed by marginal resource cost — and require each expert to beat it.
The `break_log` proposed in [04-target-architecture.md](04-target-architecture.md)
is the only component in the system capable of producing ground truth.
