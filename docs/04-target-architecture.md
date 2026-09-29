# Target Architecture

The destination, not the present. See
[../processing/PROCESSING.md](../processing/PROCESSING.md) for current behavior
and [03-current-state-audit.md](03-current-state-audit.md) for why this change
is needed.

## Design Principle

> `processing/` holds **common heuristics and building blocks**. Experts
> assemble groups from that pool. A **swappable objective** decides what "good"
> means.

The blocker today is that experts own the definition of good
([03-current-state-audit.md](03-current-state-audit.md), "Structural Blocker"),
so the objective cannot evolve from recipe overlap to profit without rewriting
every expert. The architecture below exists primarily to create that seam.

## Module Layout

```text
processing/
  blocks/              pure, stateless, config-free
    similarity.py        jaccard, idf, cosine        (replaces 4 copies)
    recipes.py           resource sets, quantities, aggregation
    shopping_list.py     line items, units, merge()
  valuation/           "what is a group worth" - swappable
    density.py           RUNE_DENSITY, validated against reference
    focus.py             D_no_focus, D_focus(f), best-focus selection
    taux.py              TauxModel: posterior over tau, decay-aware
    prices.py            PriceSource: rune prices -> rho, resource prices
    objective.py         GroupObjective protocol
    overlap.py           OverlapObjective  (price-free, today's role)
    economic.py          ProfitObjective   (target)
  policy.py            admissibility only: size, line-item cap, unit budget
  experts/             search strategies. Receive an objective. Own no formula.
  selection.py         portfolio assembly and dedup
  orchestrator.py      dispatch only

data/
  break_log            (item_id, focus, runes_received, observed_at)
  price_cache          rune and resource prices, with staleness
```

Three moves out of `processing/`: `stat_calculator.py` becomes
`valuation/density.py`; portfolio assembly leaves `orchestrator.py` for
`selection.py`; summary printing leaves `orchestrator.py` entirely.

## The Objective Seam

```python
class GroupObjective(Protocol):
    def score(self, group: GroupCandidate) -> float: ...
    def marginal(self, group: GroupCandidate, item: Equipment) -> float: ...
```

`marginal()` matters as much as `score()`. Every expert's inner loop is really
"which item do I add next":

- the random builder's companion sort,
- the genetic expert's `add` mutation and its greedy `_create_graph_individual`,
- any future beam or greedy search.

Today each answers with its own private overlap heuristic
([03-current-state-audit.md](03-current-state-audit.md), Failing 3). Given
`marginal()`, all of them become objective-agnostic search strategies, and
swapping `OverlapObjective` for `ProfitObjective` is a one-line change at the
orchestrator.

**`marginal()` must have a default implementation:**

```python
def marginal(self, group, item):
    return self.score(group.with_item(item)) - self.score(group)
```

Objectives override it only when they can compute the delta more cheaply. This
is correct by construction and fast where it matters.

**The default is not an optimisation detail — it is a correctness requirement.**
The objective in [02-objective-model.md](02-objective-model.md) is **not
additive over items**: $\tau_i$ depends on production volume $n_i$, and the
$\lambda$ term applies to the *union* of resources. An expert that assumes item
values can be summed independently will be wrong once `ProfitObjective` lands.
The default forces every objective to express incremental value in terms of the
whole group.

## Policy Versus Objective

Keep these strictly separate. They are conflated today, which is the root of
Failings 2, 4, and 7.

| Concern | Question | Lives in |
| --- | --- | --- |
| **Policy** | Is this group *admissible*? | `policy.py` |
| **Objective** | Is this group *good*? | `valuation/` |

`policy.py` owns hard constraints only, and every expert calls the same
instance:

- group size bounds,
- **maximum distinct line items** (new — see Failing 4),
- **unit budget** for carry capacity (new),
- minimum shared resources.

Everything else — reuse, compactness, revenue, cost — is objective, not policy.
`sharing_efficiency` should be retired as a *gate* and retained only as a
reported field (Failing 7).

## Valuation Layer Detail

### `density.py`

`RUNE_DENSITY`, relocated from `stat_calculator.py`. Add a test validating
entries against a published reference — the values feed revenue directly and are
currently unvalidated ([01-domain-model.md](01-domain-model.md)).

### `focus.py`

Implements the verified formulas:

```python
def break_density(item) -> float: ...                 # sum(v_s * d_s)
def break_density_focused(item, stat) -> float: ...   # v_f*d_f + 0.5*sum(rest)
def best_focus(item, rho: Mapping[str, float]) -> str | None: ...
```

`best_focus` needs rune prices; the two density functions do not. **This module
is implementable today with no external data** and is the highest
value-per-risk work available.

### `taux.py`

```python
class TauxModel(Protocol):
    def expected(self, item_id: int, planned_volume: int) -> float: ...
    def exploration_bonus(self, item_id: int) -> float: ...
```

- `FlatTauxModel` — returns a constant. Lets `ProfitObjective` ship before any
  break data exists.
- `PosteriorTauxModel` — fitted from `break_log`, decaying in `planned_volume`.

The exploration bonus is a first-class term, not a heuristic add-on: discovering
a high-taux item is the project's actual product
([01-domain-model.md](01-domain-model.md)).

### `prices.py`

```python
class PriceSource(Protocol):
    def resource_price(self, resource_id: int) -> float | None: ...
    def rune_price(self, stat: str) -> float | None: ...
    def depth(self, item_id: int) -> Sequence[tuple[float, int]] | None: ...
```

`depth` powers the market-impact term. Every method returns `None` on a miss —
objectives must degrade to the price-free path rather than assume zero, since a
missing price silently valued at zero would make an item look infinitely
profitable.

## Data Layer Additions

**`break_log`** is the only source of ground truth in the system and the only
component that can calibrate $\tau$. It should be written from the start, even
before anything reads it, because its value is proportional to history length.

```text
break_log(item_id, item_level, focus, runes_received_json, observed_at)
```

**`price_cache`** mirrors the existing resource cache, with explicit staleness —
a stale price is worse than a missing one, because it is silently wrong.

## Experts After The Change

Experts keep their identities but lose their formulas:

| Expert | Retained role |
| --- | --- |
| Graph | Community detection over a similarity graph; structural candidates |
| Random | Stochastic seed-and-grow; diversity of proposals |
| Genetic | Global search over partitions; escapes local optima |

Each receives `(blocks, policy, objective)` and returns candidate groups. The
constructor hyperparameters currently unique to the genetic expert should move
into config so instantiation is uniform.

The name "committee" should change or the behavior should. It is a
union-with-dedup, not a mixture of experts: no gating, no weighting, and all
experts ranked by the identical score
([03-current-state-audit.md](03-current-state-audit.md)). `selection.py` is the
honest home for that logic.

## Invariants To Preserve

1. `GroupMetrics.build_group_dict()` stays the single constructor of the
   canonical group schema.
2. Contract tests in `test/` continue to pass, or are updated in the same change
   with a stated reason.
3. `PROCESSING.md` is updated in the same change as any behavior change.
4. Objectives are pure functions of a group plus injected data sources — no
   global state, no module-level `random`.
