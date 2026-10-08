# RuneMaster: Statement of Goal and Clean-Slate Todo

**Purpose:** This document is the entry point for any agent (human or LLM) joining
RuneMaster. It states the end goal, challenges that goal against the game mechanic,
records how the new knowledge changes prior reviews, and lays out the step-by-step
work required to reach a clean slate from which a frontier model can iterate on
strategy.

**Read order for new agents:**
1. This document — the goal and the plan
2. [01-domain-model.md](01-domain-model.md) — the game mechanic
3. [02-objective-model.md](02-objective-model.md) — the profit equation
4. [03-current-state-audit.md](03-current-state-audit.md) — what is wrong today
5. [04-target-architecture.md](04-target-architecture.md) — the target design
6. [05-roadmap.md](05-roadmap.md) — staged plan and open decisions

---

## 1. Statement of the End Goal

RuneMaster exists to **maximize profit from a craft-break-sell loop** in Dofus 3.

The loop:
1. Buy crafting resources on the market.
2. Craft a set of different equipment items.
3. Break those items in the concasseur to obtain runes.
4. Sell the runes on the market.

The profit of a production run is:

$$\text{Profit} = \sum_{i \in G} n_i \cdot \mathbb{E}[\tau_i(n_i)] \cdot D_i(f_i) \cdot \rho_{f_i} \;-\; \sum_{i \in G} n_i \cdot c_i \;-\; \lambda \cdot \left|\bigcup_i R_i\right| \;-\; \text{impact}$$

Where:
- $G$ = the group of items to craft
- $n_i$ = how many of item $i$ to produce
- $\tau_i(n_i)$ = the break rate (taux) of item $i$, decaying in $n_i$
- $D_i(f_i)$ = break density under focus $f_i$ (from the rune density table)
- $\rho_{f_i}$ = market price per unit density of rune $f_i$
- $c_i$ = craft cost of item $i$ at spot resource prices
- $\lambda$ = fixed acquisition cost per distinct resource
- $\bigcup_i R_i$ = the union of all resources needed
- impact = order-book walk penalty for large orders

**The grouping problem** is the sub-problem of choosing $G$: a set of items whose
recipes share resources, so that the shopping list is short and cheap, while the
items are diverse enough to discover high-taux opportunities.

**The discovery problem** is the meta-problem: $\tau_i$ is unknowable before
breaking, so the system must explore (break many different item types) while
exploiting (break known high-taux items while their taux holds).

**The end goal is not** "maximize recipe overlap." Overlap is the mechanism that
makes exploration affordable. The goal is profit.

---

## 2. Weaknesses of the End Goal

These are weaknesses in the goal itself — assumptions that may be wrong or
incomplete — not implementation bugs. Each is tagged with its status.

### W1 — The goal assumes grouping is the decision unit, but the real decision is a production plan

**[INFERRED]** The current architecture treats "find good groups" as the problem.
But the actual decision a player faces is: *which items to craft, how many of each,
and when to stop breaking them.* A group is a constraint (shared resources), not
the objective. The optimal production plan may not correspond to any single
"group" — it may be a sequence of overlapping groups crafted in phases as taux
values are discovered.

**Consequence:** Optimizing group quality in isolation may produce groups that
are suboptimal as production plans. The system needs to reason about sequences
of groups and the information gained between them.

### W2 — The goal cannot be optimized without ground truth that does not yet exist

**[VERIFIED-GAME]** $\tau$ ranges from 1% to 4000% and cannot be known before
breaking. This is a 40x swing that dominates every other term. No objective
function that ignores $\tau$ can rank items correctly.

**Consequence:** The entire current pipeline optimizes a proxy (recipe overlap)
that is uncorrelated with the dominant term. Until `break_log` exists and has
accumulated observations, the system cannot evaluate its own output. This is
not a bug to fix — it is a fundamental epistemic limitation. The system must
be designed to *collect* the data it needs before it can *optimize* against it.

### W3 — The goal assumes static prices, but prices change

**[INFERRED]** Rune and resource prices fluctuate with the market. A group that
is profitable today may not be tomorrow. The current architecture has no notion
of price staleness or re-evaluation.

**Consequence:** The system should treat prices as time-sensitive data with
explicit freshness, and should be able to re-evaluate groups when prices change.
This is partially addressed by the `price_cache` design in
[04-target-architecture.md](04-target-architecture.md), but the re-evaluation
trigger and strategy are unspecified.

### W4 — The goal does not model the opportunity cost of the player's time

**[INFERRED]** Crafting, breaking, and selling all take time. A group of 50
items that yields 10% more profit but takes 3x longer to craft may be worse
than a smaller group. The current objective has no time term.

**Consequence:** The $\lambda$ parameter partially captures this (time spent
acquiring resources), but crafting and breaking time are unmodelled. This may
be acceptable as a v1 simplification but should be recorded as a known gap.

### W5 — The goal assumes the player can sell runes at the listed price

**[INFERRED]** Selling runes also walks the order book. The `impact` term in
the objective acknowledges this, but no depth data exists to model it. Without
it, the system may overestimate profit for large runs.

**Consequence:** The impact term is correctly identified as needing market
depth data. Until that data exists, profit estimates are upper bounds.

### W6 — The goal conflates "easy to craft" with "profitable"

**[INFERRED]** The current `quality_score` and the proposed compression metric
measure shopping-list compactness. But a compact shopping list is not
profitable if the items break into low-value runes. The $\lambda$ term in the
profit equation is the correct bridge, but $\lambda$ is unknown and likely
varies by player (some players value time more than others).

**Consequence:** The system needs a user-calibratable $\lambda$ and should
report profit estimates alongside compactness metrics, not instead of them.

### W7 — The goal does not account for item level constraints on crafting

**[INFERRED]** Crafting requires a minimum profession level. The current
pipeline filters by item level but does not check whether the player's
profession level is sufficient to craft the items in a group.

**Consequence:** Groups may contain items the player cannot craft. This is
a data gap (the player's profession levels are not in the system) rather
than an architectural one, but it affects the validity of the output.

---

## 3. How the New Knowledge Challenges the Prior Review

The prior architectural review (this conversation, before the rune mechanic
guide was introduced) identified weaknesses in the *implementation*. The new
knowledge — the actual game mechanic — challenges the review's *framing*.

### 3.1 What the prior review got right (still valid)

- **Lossy pairwise graph projection** — still true. Jaccard on resource IDs
  discards quantity and rarity information.
- **Evolutionary committee is expensive** — still true, but see 3.2 below.
- **Synchronous I/O bottleneck** — still true and independent of the objective.
- **Type safety gaps** — still true and independent of the objective.
- **God-object config** — still true and independent of the objective.

These are implementation weaknesses that must be fixed regardless of what
the objective becomes.

### 3.2 What the prior review got wrong or premature

**The optimization hypotheses were solving the wrong problem.**

The prior review proposed:
- ILP Set Cover formulation
- Bipartite graph community detection
- Weighted Jaccard with quantity awareness

These all optimize *recipe overlap*. But the game mechanic reveals that recipe
overlap is not the objective — it is one term ($\lambda \cdot |\bigcup R_i|$)
in a profit equation dominated by $\tau$, which is unknowable. An ILP solver
that perfectly optimizes recipe overlap still cannot tell you which items
are worth breaking.

**The critique of the evolutionary committee was misguided.**

The prior review called the evolutionary committee "computationally expensive
with no convergence guarantee." But the real problem is not that the search
is expensive — it is that the *fitness function* is a proxy uncorrelated with
the true objective. Making the search faster (ILP, better heuristics) does
not fix a wrong objective. The search strategy is secondary to the valuation
layer.

**The type safety critique was solving a second-order problem.**

The prior review identified that experts return unstructured dicts and that
the objective cannot be swapped. This is true, but the solution (Pydantic
models, `GroupObjective` protocol) is only valuable if there is a correct
objective to plug in. Until the valuation layer has rune density, focus,
taux, and prices, the seam has nothing to connect.

### 3.3 What the new knowledge changes about the roadmap

The prior review proposed three phases:
1. Data layer & solver decoupling
2. High-performance solver engine
3. Code quality & benchmarking

The new knowledge reorders this:

1. **Valuation layer first** — the objective must exist before it can be
   optimized. This means: rune density, focus formula, taux model, price
   source. Without these, any solver is optimizing a guess.
2. **Data collection second** — `break_log` must start accumulating
   observations immediately. The value of this data scales with history
   length; every week of not logging is permanently lost calibration data.
3. **Solver improvement third** — only once the objective is real does it
   make sense to optimize the search. ILP, bipartite detection, and other
   solver improvements are valuable but premature.

### 3.4 The fundamental challenge

The prior review asked: *"How do we find better groups?"*

The new knowledge reveals the real question is: *"How do we discover which
items are worth breaking, given that the answer changes every time we break
them?"*

These are different problems. The first is a clustering problem. The second
is a bandit problem with decaying rewards. The current architecture is
designed for the first. The second requires:
- A data collection mechanism (`break_log`)
- A valuation model that incorporates uncertainty (`PosteriorTauxModel`)
- An exploration strategy (which items to try next)
- A re-evaluation trigger (when to update beliefs and re-plan)

---

## 4. Clean-Slate Todo: Step-by-Step for Future Agents

This section is the actionable plan. Each step is atomic — it can be
independently verified and rolled back. The steps are ordered by dependency.

### Phase 0: Foundation (no behavior change)

These steps create the seams that everything else depends on. They are
pure refactors — no output changes.

#### Step 0.1: Extract `blocks/similarity.py`

**What:** Create a single module for all similarity functions. Replace the
four existing Jaccard implementations (in `quality_metrics.py`,
`orchestrator.py`, `graph_builder.py`, and `community_detector.py`).

**Why:** Eliminates duplication and creates a single place to add
quantity-weighted and IDF-weighted similarity later.

**Files:**
- Create: `processing/blocks/similarity.py`
- Modify: `processing/quality_metrics.py`, `processing/orchestrator.py`,
  `processing/graph_builder.py`, `processing/community_detector.py`

**Acceptance:** All existing tests pass. `jaccard()` is importable from
`processing.blocks.similarity` and produces identical results.

#### Step 0.2: Extract `blocks/shopping_list.py`

**What:** Create a `ShoppingList` value object that encapsulates line items,
units, and merge operations. Extract the logic currently split between
`GroupMetrics.aggregate_resources()` and `html_generator.py`.

**Why:** The shopping list is the product. Making it a first-class object
gives it a home for cost modeling and makes plan 04's "combine groups"
a `merge()` operation.

**Files:**
- Create: `processing/blocks/shopping_list.py`
- Modify: `processing/group_metrics.py`, `visualization/html_generator.py`

**Acceptance:** `ShoppingList` can be constructed from a group dict,
reports `line_item_count` and `total_units`, and supports `merge(other)`.

#### Step 0.3: Introduce `GroupObjective` protocol

**What:** Define the objective seam. Implement `OverlapObjective` wrapping
today's `quality_score` exactly. Give `marginal()` a default implementation
of `score(G + item) - score(G)`.

**Why:** This is the seam that makes the objective swappable. Without it,
every future change to the valuation layer requires editing every expert.

**Files:**
- Create: `processing/valuation/objective.py` (already exists, extend it)
- Modify: `processing/experts/base.py` — experts receive an objective
- Modify: `processing/orchestrator.py` — dispatch objective to experts

**Acceptance:** `OverlapObjective` produces scores identical to the current
`quality_score`. Experts can be instantiated with any `GroupObjective`
implementation. Contract tests pass.

#### Step 0.4: Extract `policy.py`

**What:** Create a single `GroupAcceptancePolicy` that every expert calls.
Remove the triple-applied thresholds (in `group_mapper.py`,
`genetic_expert.py`, `random_expert.py`).

**Why:** Eliminates the divergent filter semantics (Failing 2 and 7 in
[03-current-state-audit.md](03-current-state-audit.md)).

**Files:**
- Create: `processing/policy.py` (already exists, consolidate)
- Modify: `processing/experts/*.py` — call the shared policy
- Modify: `processing/group_mapper.py` — delegate to policy

**Acceptance:** A contract test asserts that the graph path and genetic
path accept the identical set of candidate groups given the same config.

#### Step 0.5: Delete dead code

**What:** Remove `resource_optimizer.py`, `use_resource_optimizer`,
`calculate_bulk_efficiency`, and the unused `api_client` threading.

**Why:** Reduces surface area and confusion.

**Files:**
- Delete: `processing/resource_optimizer.py`
- Modify: `processing/config_dataclass.py` — remove `use_resource_optimizer`
- Modify: `processing/community_detector.py` — remove `calculate_bulk_efficiency`
- Modify: `processing/group_metrics.py` — remove `api_client` parameter

**Acceptance:** `python -m compileall` passes. No references to deleted
symbols remain.

#### Step 0.6: Replace global `random` with injected instances

**What:** Replace `random.seed()` and module-level `random` calls with
`random.Random(seed)` instances passed through constructors.

**Why:** The current code is unsafe under `ProcessPoolExecutor` (used by
the tuner) and makes reproducibility impossible to guarantee.

**Files:**
- Modify: `processing/random_group_builder.py`
- Modify: `processing/experts/genetic_expert.py`
- Modify: `processing/experts/random_expert.py`
- Modify: `processing/tuner.py`

**Acceptance:** Two runs with the same seed produce identical output.
Tuner workers are independent.

### Phase 1: Valuation Layer (changes output)

These steps implement the game math. They change what the system optimizes.

#### Step 1.1: Move and validate `RUNE_DENSITY`

**What:** Move `STAT_WEIGHTS` from `stat_calculator.py` to
`valuation/density.py` as `RUNE_DENSITY`. Add a validation test against
the published density reference.

**Why:** The density table is a core game constant that feeds revenue
directly. It must be validated and live in the valuation layer.

**Files:**
- Create: `processing/valuation/density.py` (already exists, extend)
- Modify: `processing/stat_calculator.py` — re-export for compatibility
- Create: `test/test_density_table.py`

**Acceptance:** Every entry in `RUNE_DENSITY` is validated against a
published reference. The `% Résistance` (6) vs flat `Résistance` (2)
split is confirmed. `Dommages` (5), `Sagesse` (3), etc. are confirmed.

#### Step 1.2: Implement focus formulas

**What:** Implement `break_density(item)`, `break_density_focused(item, stat)`,
and `best_focus(item, rho)` in `valuation/focus.py`.

**Why:** These are pure game math, exactly specified by the guide. They
convert stat lines to rune yield estimates. No prices needed for the first
two; `best_focus` needs rune prices.

**Files:**
- Modify: `processing/valuation/focus.py` (already exists, extend)
- Create: `test/test_focus.py`

**Acceptance:** For a known item with known stat lines, `break_density`
returns the expected value. `break_density_focused` correctly applies the
half-density penalty to non-focus lines. `best_focus` returns the stat
with the highest `D_focus(f) * rho_f`.

#### Step 1.3: Add compression term to `OverlapObjective`

**What:** Add the compression metric to `GroupQualityEvaluator` and reweight:
- compression: 0.50
- `resource_reuse_ratio`: 0.30
- `shared_quantity_ratio`: 0.20

Remove `mean_pairwise_jaccard` and `overlapping_pair_ratio` from scoring
(retain as reported diagnostics).

**Why:** The current features are scale-invariant ratios that decay with
group size, biasing the system toward pairs. Compression is extensive —
it rewards adding items that don't lengthen the shopping list.

**Files:**
- Modify: `processing/quality_metrics.py`
- Modify: `processing/valuation/overlap.py`
- Create: `test/test_compression.py` (already exists, extend)

**Acceptance:** A unit test asserts monotonicity: appending an item whose
recipe is a subset of the group's existing resource union must not lower
the score. Group-size distribution shifts upward in integration tests.

#### Step 1.4: Move constraints onto line items and units

**What:** Add `max_line_items` (cap on `unique_resource_count`) and
`max_total_units` (cap on `total_items_needed`) to the policy. Let
group size float upward.

**Why:** The cost of a shopping list is its length and weight, not the
number of items it produces. A 20-item group needing 9 resources is a
better list than a 4-item group needing 40.

**Files:**
- Modify: `processing/policy.py`
- Modify: `processing/config_dataclass.py`
- Modify: `processing/group_metrics.py` — expose `unique_ingredients_count`
  and `total_items_needed` to the policy

**Acceptance:** A group with 20 items and 9 distinct resources passes
the policy. A group with 4 items and 40 distinct resources fails.

#### Step 1.5: Retire `sharing_efficiency` as a gate

**What:** Remove `group_efficiency_threshold` from the acceptance policy.
Keep `sharing_efficiency` as a reported field.

**Why:** It duplicates `quality_score` with worse semantics (excluded
resources in the denominator but not the numerator). Two gates that
measure the same thing incompatibly cause unpredictable tuning behavior.

**Files:**
- Modify: `processing/policy.py`
- Modify: `processing/config_dataclass.py`
- Modify: `processing/group_mapper.py`

**Acceptance:** Groups previously rejected by the efficiency gate but
passing the quality gate are now accepted. No test references
`group_efficiency_threshold` as a gate.

#### Step 1.6: Move the value gate into the loader

**What:** Move density filtering from the random expert into
`data/loaders.py`. Switch from a linear-in-level threshold to a
within-level-band percentile.

**Why:** The gate currently covers one of five execution paths. All
methods should share the same pool. A percentile filter is level-unbiased.

**Files:**
- Modify: `data/loaders.py`
- Modify: `processing/equipment_filter.py`
- Modify: `processing/experts/random_expert.py` — remove inline filter

**Acceptance:** All five grouping methods receive the same equipment
pool. No emitted group contains an item below the configured percentile.

### Phase 2: Data Collection (no immediate output change)

These steps build the ground-truth infrastructure. They do not change
output yet but enable all future optimization.

#### Step 2.1: Create `break_log` table and writer

**What:** Add a `break_log` table to `CacheManager` with columns:
`item_id, item_level, focus, runes_received_json, observed_at, source`.
Add `record_break_observation()` and `list_break_observations()` methods.

**Why:** This is the only source of ground truth in the system. Its value
scales with history length — start logging before anything reads it.

**Files:**
- Modify: `data/cache_manager.py`
- Create: `test/test_break_log.py`

**Acceptance:** Can record and retrieve break observations. The table
is exempt from cache clearing.

#### Step 2.2: Create `price_cache` table and `PriceSource`

**What:** Add a `price_cache` table to `CacheManager` with columns:
`item_id, kind, unit_price, observed_at, source`. Implement `PriceSource`
protocol with `NullPriceSource` (returns `None` for everything) and
`CachePriceSource`.

**Why:** Prices are needed for the profit objective. The schema must exist
before data does, so Phase 3 is a data change, not a refactor.

**Files:**
- Modify: `data/cache_manager.py`
- Modify: `processing/valuation/prices.py`
- Create: `test/test_price_cache.py`

**Acceptance:** `NullPriceSource` returns `None` for all queries.
`CachePriceSource` retrieves stored prices with staleness detection.

#### Step 2.3: Implement `FlatTauxModel`

**What:** Implement a `TauxModel` that returns a constant taux for all
items. This lets `ProfitObjective` ship before any break data exists.

**Why:** The objective must be testable before real data is available.
A flat taux is the simplest possible model.

**Files:**
- Modify: `processing/valuation/taux.py`
- Create: `test/test_flat_taux.py`

**Acceptance:** `FlatTauxModel.expected(item_id, volume)` returns the
constant regardless of inputs. `exploration_bonus` returns zero.

### Phase 3: Profit Objective (changes output)

These steps wire the valuation layer into the objective. They change
what the system optimizes from overlap to profit.

#### Step 3.1: Implement `ProfitObjective`

**What:** Implement `ProfitObjective` that combines:
- Revenue: `taux * break_density * rho`
- Cost: `sum(quantity * resource_price)`
- Acquisition: `lambda * distinct_resource_count`
- Exploration: `taux_model.exploration_bonus(item_id)`

Use `FlatTauxModel` and `NullPriceSource` as defaults.

**Why:** This is the objective the system should actually optimize. It
replaces `OverlapObjective` as the default.

**Files:**
- Create: `processing/valuation/economic.py`
- Modify: `processing/orchestrator.py` — use `ProfitObjective` by default
- Create: `test/test_profit_objective.py`

**Acceptance:** `ProfitObjective.score()` returns a float. With
`NullPriceSource`, it degrades to the price-free path (revenue = 0,
cost = 0, only acquisition cost and exploration bonus remain). With
`FlatTauxModel` and `CachePriceSource`, it returns a profit estimate.

#### Step 3.2: Wire `best_focus` into the objective

**What:** When rune prices are available, `ProfitObjective` uses
`best_focus(item, rho)` to select the focus that maximizes revenue.
When prices are unavailable, it uses no-focus density.

**Why:** Focus is a decision variable. The objective should choose the
best focus given current prices.

**Files:**
- Modify: `processing/valuation/economic.py`
- Modify: `processing/valuation/focus.py`

**Acceptance:** Given a known item and known rune prices, `ProfitObjective`
selects the focus that maximizes `D_focus(f) * rho_f`.

#### Step 3.3: Add resource-overlap-awareness to portfolio selection

**What:** Modify `PortfolioSelector` to treat cross-group resource
overlap as neutral or positive, while keeping equipment dedup.

**Why:** Two groups sharing resources is one bulk purchase serving two
runs — strictly good. The current scoring penalizes exactly the property
that plan 04 (combined shopping list) depends on.

**Files:**
- Modify: `processing/selection.py`
- Create: `test/test_portfolio_resource_overlap.py`

**Acceptance:** A portfolio whose groups share resources scores higher
than one whose groups are resource-disjoint, all else equal.

### Phase 4: Exploration Strategy (changes output)

These steps implement the bandit logic. They change which items the
system recommends.

#### Step 4.1: Implement `PosteriorTauxModel`

**What:** Implement a `TauxModel` that maintains a posterior over $\tau$
per item type, fitted from `break_log`. The model should:
- Use a prior (e.g., uniform over [1%, 4000%])
- Update the posterior with each observation
- Decay the posterior in planned production volume
- Provide an exploration bonus for item types with few observations

**Why:** This is the actual edge of the system. It converts break
observations into actionable intelligence about which items to craft.

**Files:**
- Modify: `processing/valuation/taux.py`
- Create: `test/test_posterior_taux.py`

**Acceptance:** Given a set of break observations, the model produces
a posterior mean and variance for $\tau$. The posterior mean is higher
for items with more observations. The exploration bonus is higher for
items with fewer observations.

#### Step 4.2: Wire `PosteriorTauxModel` into `ProfitObjective`

**What:** Replace `FlatTauxModel` with `PosteriorTauxModel` in
`ProfitObjective` when break data is available.

**Why:** The objective should use the best available estimate of $\tau$.

**Files:**
- Modify: `processing/valuation/economic.py`
- Modify: `processing/orchestrator.py`

**Acceptance:** When `break_log` has observations, `ProfitObjective`
uses `PosteriorTauxModel`. When it is empty, it falls back to
`FlatTauxModel`.

#### Step 4.3: Implement exploration shortlist

**What:** Create a ranked list of items worth trying, based on:
- Theoretical break density per resource unit
- Exploration bonus from `PosteriorTauxModel`
- Time since last observation

**Why:** This is the user-facing output of the bandit logic. It answers
"what should I craft next to discover high-taux items?"

**Files:**
- Modify: `processing/exploration.py` (already exists, extend)
- Create: `test/test_exploration_shortlist.py`

**Acceptance:** The shortlist ranks items by exploration value. Items
with no observations rank higher than items with many observations
(all else equal). The list updates as observations are added.

### Phase 5: Solver Improvement (changes output)

These steps improve the search. They are only valuable once the objective
is real.

#### Step 5.1: Add greedy baseline

**What:** Implement a trivial baseline: top-K items by value density,
greedily packed by marginal resource cost.

**Why:** No expert has ever been compared to a trivial baseline. This is
the only way to know whether graph detection and the genetic algorithm
are earning their complexity.

**Files:**
- Create: `processing/experts/baseline_expert.py` (already exists, extend)
- Create: `test/test_baseline_comparison.py`

**Acceptance:** The baseline produces groups. Each expert's output is
compared to the baseline on the objective. Experts that do not beat
the baseline are flagged.

#### Step 5.2: Evaluate ILP Set Cover as an alternative to evolutionary search

**What:** Implement an ILP formulation of the grouping problem using
OR-Tools CP-SAT. The objective is to maximize profit subject to:
- Group size bounds
- Line item cap
- Unit budget
- Each item assigned to at most one group

**Why:** The evolutionary committee is expensive with no convergence
guarantee. An ILP solver can find provably optimal or near-optimal
solutions for ~500 items in seconds.

**Files:**
- Create: `processing/solvers/ilp_solver.py`
- Create: `test/test_ilp_solver.py`

**Acceptance:** The ILP solver produces groups with a profit estimate
at least as good as the evolutionary committee, in less time.

#### Step 5.3: Benchmark all solvers head-to-head

**What:** Create a benchmark suite comparing: deterministic, committee,
evolutionary_committee, ILP, and baseline. Metrics: runtime, profit
estimate, group count, line item count.

**Why:** Provides objective evidence for solver selection.

**Files:**
- Create: `test/benchmark/test_solvers.py`
- Create: `docs/06-solver-comparison.md`

**Acceptance:** Benchmark results are stored as JSON. The comparison
document recommends a default solver with evidence.

### Phase 6: Capture Integration (changes output)

These steps connect the OCR capture module to the valuation layer.

#### Step 6.1: Implement price capture

**What:** Extend the capture module to scrape rune and resource prices
from the game window and feed them into `price_cache`.

**Why:** Manual price entry does not scale. The capture module removes
the bottleneck.

**Files:**
- Modify: `capture/price_ingestion.py`
- Modify: `data/cache_manager.py`

**Acceptance:** Prices captured from the game window are stored in
`price_cache` with a timestamp. `CachePriceSource` retrieves them.

#### Step 6.2: Implement break result capture

**What:** Extend the capture module to scrape break results from the
game window and feed them into `break_log`.

**Why:** Break results are the only ground truth. Manual logging is
error-prone and incomplete.

**Files:**
- Modify: `capture/break_ingestion.py`
- Modify: `data/cache_manager.py`

**Acceptance:** Break results captured from the game window are stored
in `break_log` with item ID, focus, runes received, and timestamp.
`PosteriorTauxModel` uses them.

---

## 5. What This Plan Delivers

When all six phases are complete, the system will:

1. **Value items correctly** — using rune density, focus, taux, and prices
   to estimate profit, not just recipe overlap.
2. **Learn from experience** — `break_log` accumulates observations and
   `PosteriorTauxModel` converts them into actionable intelligence.
3. **Explore intelligently** — the exploration shortlist recommends which
   items to craft next, balancing exploitation of known high-taux items
   with exploration of unknown ones.
4. **Optimize the search** — the ILP solver finds near-optimal groups
   in seconds, and the benchmark suite provides evidence for solver
   selection.
5. **Adapt to market changes** — price capture feeds fresh data into
   the objective, and the system re-evaluates groups when prices change.

The frontier model can then iterate on strategy — trying different
solvers, different exploration strategies, different valuation models —
against a system that can actually evaluate the results.

---

## 6. Open Questions That Block Progress

These must be resolved before the corresponding phase can start.

| Question | Blocks | How to resolve |
|---|---|---|
| Where do rune and resource prices come from? | Phase 3 | Data-sourcing decision: community API, scrape, or manual entry |
| Is the taux per item type or per item instance? | Phase 4 | Observation: break the same item type repeatedly and watch the taux |
| What is $\lambda$ worth in kamas? | Phase 3 | User calibration: ask the player what a market round-trip is worth |
| What is the density-to-rune-count conversion? | Phase 3 | Calibration: fit against `break_log` observations |
| Does the taux recover over time? | Phase 4 | Observation: stop breaking an item type for a week, then break it again |

---

## 7. Relationship to Other Documents

- This document is the **entry point** for new agents.
- [01-domain-model.md](01-domain-model.md) covers the game mechanic in detail.
- [02-objective-model.md](02-objective-model.md) covers the profit equation.
- [03-current-state-audit.md](03-current-state-audit.md) covers implementation weaknesses.
- [04-target-architecture.md](04-target-architecture.md) covers the target module layout.
- [05-roadmap.md](05-roadmap.md) covers the staged plan and open decisions.
- [../processing/PROCESSING.md](../processing/PROCESSING.md) is authoritative for
  current behavior. Where these documents disagree about the present,
  `PROCESSING.md` is right.

---

## 8. Status Legend

| Tag | Meaning |
|---|---|
| **[VERIFIED-GAME]** | Stated directly by the cited game guide. |
| **[VERIFIED-CODE]** | Confirmed by reading the repository at the cited path. |
| **[INFERRED]** | A model derived from verified facts. Plausible, not confirmed. |
| **[UNKNOWN]** | Open question. Must be measured or researched before relying on it. |
