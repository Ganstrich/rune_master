# Roadmap And Open Decisions

Sequenced so each stage is independently useful and none blocks on data that
does not exist yet. See [04-target-architecture.md](04-target-architecture.md)
for the target shape.

## Stage A — Seams

**Behavior-preserving.** No output changes; contract tests should pass
untouched.

- Extract `blocks/similarity.py`; replace the four Jaccard implementations.
- Extract `blocks/recipes.py` and `blocks/shopping_list.py`.
- Introduce `GroupObjective` with `score()` and `marginal()`; implement
  `OverlapObjective` wrapping today's `quality_score` exactly.
- Extract `policy.py`; every expert calls the same instance. Removes the
  triple-applied thresholds and the divergent `resource_reuse_ratio` versus
  `sharing_efficiency` filter (Failing 2).
- Move portfolio assembly out of `orchestrator.py` into `selection.py`.
- Delete `resource_optimizer.py`, `use_resource_optimizer`,
  `calculate_bulk_efficiency` (dead and wrong), and the unused `api_client`
  threading.
- Replace module-level `random` with injected `Random` instances — currently
  unsafe under the tuner's `ProcessPoolExecutor`.

**Unblocks:** everything. Without this, Stages B-D are rewrites rather than
additions.

## Stage B — Density And Focus

**Requires no external data.** Pure game math, exactly specified by the source.

- Move `STAT_WEIGHTS` to `valuation/density.py` as `RUNE_DENSITY`; add a
  validation test against a published reference.
- Implement `valuation/focus.py`: `break_density`, `break_density_focused`.
- Surface break density per item in reports.
- Add the compression term to `OverlapObjective` and reweight (Failing 1).
- Move constraints onto line items and unit budget (Failing 4).
- Retire `sharing_efficiency` as a gate; keep it as a reported field
  (Failing 7).
- Move the value gate into the loader so all five methods share it, and switch
  from a linear-in-level threshold to a within-level-band percentile
  (Failing 6).

**Unblocks:** correct item valuation structure; fixes the size bias that makes
every current search converge on pairs.

**Changes output.** Group composition will shift noticeably. Capture a
before/after on group-size and line-item distributions.

## Stage C — Prices

**Blocked on a price feed.** Resolve sourcing before committing.

- `data/price_cache` with explicit staleness.
- `valuation/prices.py` implementing `PriceSource`.
- `valuation/economic.py`: `ProfitObjective` with `FlatTauxModel`.
- `best_focus(item, rho)` becomes live.
- Market-impact term, if depth data is available.
- Add resource-overlap-awareness across groups in `selection.py` (Failing 5).

**Open:** where rune and resource prices come from. A community market API, a
scrape, or manual entry are all viable; this is a data-sourcing decision more
than an engineering one.

## Stage D — Taux

**The actual edge.** Nothing else in the system produces ground truth.

- `data/break_log`, written from the earliest possible date — its value scales
  with history length, so start logging before anything reads it.
- `valuation/taux.py`: `PosteriorTauxModel`, fitted from the log.
- Decay of expected taux in planned production volume.
- Exploration bonus for item types with few or no observations.

**Unblocks:** the project's stated purpose — discovering which items carry a
high coefficient.

## Suggested Order Within Constraints

`A -> B` first; both are self-contained and B delivers real improvement.
Begin `break_log` writes during A or B regardless of when D starts, since the
data is only useful retrospectively. `C` waits on the price-source decision.

## Open Decisions

### Resolved

- **`marginal()` in the protocol.** Yes, with a default of
  `score(G + item) - score(G)`. Required for correctness, not just speed: the
  objective is non-additive because taux decays in volume and the acquisition
  cost applies to the union of resources.

- **Compression replaces the pairwise features.** `mean_pairwise_jaccard` and
  `overlapping_pair_ratio` are removed from scoring and retained as reported
  diagnostics. New weights: compression 0.50, `resource_reuse_ratio` 0.30,
  `shared_quantity_ratio` 0.20. Both removed features average over pairs and so
  decay with group size by construction; no reweighting could fix that.

### Pending

1. **Where do rune and resource prices come from?** *Blocks Stage C.*

2. **Is the taux per item type or per item instance?** The guide is ambiguous
   and the answer changes the strategy substantially. *Resolve by observation
   before Stage D.* See [01-domain-model.md](01-domain-model.md).

3. **What is $\lambda$ worth in kamas?** The fixed cost of one market
   round-trip. User-set, but needs a defensible default.

4. **Should `run_committee` be renamed or made into a real mixture of
   experts?** Currently a union-with-dedup.

## Validation Gate

Unchanged from [../processing/PROCESSING.md](../processing/PROCESSING.md):

```bash
uv run pytest -q
python3 -m compileall -q data processing main.py config.py test visualization
git diff --check
```

Additionally, before merging any stage that changes output: record group-size,
line-item-count, and portfolio-score distributions before and after, and state
which failing the change addresses.

## Future Work, Explicitly Out Of Scope

**Learning a temporal model of taux evolution.** Observations age, and
[../plans/processing/32-taux-model.md](../plans/processing/32-taux-model.md)
handles this by down-weighting them on a fixed exponential half-life. A stronger
approach would *predict* how an item's taux evolves — as a function of elapsed
time, server-wide break volume, patch cycles, or item popularity — rather than
merely discounting stale data.

This is deliberately excluded for now. The half-life stays a tunable constant.
Revisit only once `break_log` holds enough history to fit and validate a
temporal model out of sample; attempting it earlier would produce an unfalsifiable
model on top of an already-inferred yield formula.

**Market impact.** The order-book walk term in
[02-objective-model.md](02-objective-model.md) requires depth data, not just
spot prices. Deferred until a depth source exists.

## Missing Baseline

No expert has ever been compared to a trivial baseline. Before adding search
sophistication, implement one — top-K items by value density, greedily packed by
marginal resource cost — and require each expert to beat it on the objective.
This is cheap, and it is the only way to know whether graph detection and the
genetic algorithm are earning their complexity.
