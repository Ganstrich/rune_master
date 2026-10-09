# Frontier Model Iteration Prompt

## Purpose

This document is a self-contained prompt for a frontier model to iterate on
RuneMaster's stated goal: **maximize profit from a craft-break-sell loop by
discovering which items carry a high taux.**

The model should use this prompt to drive its own experimentation loop:
form a hypothesis, test it against the API, analyze the results, and adapt.

---

## Project Context

RuneMaster groups Dofus 3 equipment items by shared recipe resources so a
player can buy a short shopping list in bulk, craft many different items,
break them for runes, and sell the runes at a profit.

The critical game mechanic: each item has a **taux** (break rate, 1%–4000%)
that multiplies rune yield. The taux **cannot be known before breaking** and
**decays as an item type is broken more**. This makes the problem a bandit:
the system must explore (break many different item types) while exploiting
(break known high-taux items while their taux holds).

**Set membership is a proxy for taux.** Items from the same panoplie are the
"safe" crafting choices every player crafts — they are systematically broken
by many players and have a low taux. A group with high set concentration is
a poor exploration vehicle.

The full profit equation:

```
Value(G) = Σ E[τ_i(n_i)] · D_i(f_i) · ρ_f_i - c_i  -  λ·|∪R_i|  -  impact  -  γ·set_concentration(G)
```

Where:
- `E[τ_i(n_i)]` = expected taux, decaying in own production volume
- `D_i(f_i)` = break density under focus (from rune density table)
- `ρ_f_i` = rune price per density
- `c_i` = craft cost at spot resource prices
- `λ·|∪R_i|` = fixed acquisition cost per distinct resource
- `impact` = order-book walk penalty
- `γ·set_concentration(G)` = penalty for crafting items from the same panoplie

---

## Current State

The codebase has:
- A working pipeline: API → cache → graph → experts → HTML report
- Five grouping methods: deterministic, random, hybrid, committee, genetic
- A `GroupObjective` protocol (swappable valuation seam)
- A `GroupAcceptancePolicy` (admissibility gate)
- A `RUNE_DENSITY` table (validated against game guide)
- A `PosteriorTauxModel` (bandit logic, fitted from break observations)
- A `PriceSource` protocol with `NullPriceSource` and `CachePriceSource`
- A `break_log` table for recording break observations
- A `price_cache` table for storing market prices

The system currently optimizes a **proxy** (recipe compactness) because:
1. No price data exists yet (all prices return `None`)
2. No break observations exist yet (taux is unknown)
3. The `OverlapObjective` is the default; `ProfitObjective` is implemented
   but not wired as default

---

## Your Task: Iterate on the Goal

You are a frontier model with access to the RuneMaster codebase. Your job is
to **iterate on the stated goal** by:

1. **Forming hypotheses** about what would improve the system's ability to
   provide groups of items and maximize profit.
2. **Testing those hypotheses** using the actual API and game data.
3. **Analyzing the results** to confirm or refute the hypothesis.
4. **Adapting the system** based on what you learn.

### Iteration Loop

```
while not converged:
    hypothesis = form_hypothesis()
    experiment = design_experiment(hypothesis)
    results = run_experiment(experiment)
    analysis = analyze(results)
    if analysis.confirms(hypothesis):
        implement_change(analysis.recommended_change)
    else:
        record_negative_result(hypothesis, analysis)
    update_beliefs(analysis)
```

### What to Test

You should test hypotheses about:

**A. Item Valuation**
- Does the rune density table accurately predict rune yield?
- Does the focus formula correctly identify the best focus for each item?
- Does set membership correlate with lower taux (validating the proxy)?

**B. Group Formation**
- Do groups with high set concentration actually yield lower profit?
- Does the compression metric correctly identify groups with short shopping lists?
- Does the λ parameter (acquisition cost) need calibration?

**C. Exploration Strategy**
- Does the exploration shortlist correctly identify items worth trying?
- Does the posterior taux model converge to the true taux with enough observations?
- Does the exploration bonus correctly balance exploration vs exploitation?

**D. Market Dynamics**
- How do price changes affect group profitability?
- Does the order-book walk penalty (impact) significantly affect profit?
- Are there arbitrage opportunities between resource costs and rune prices?

### How to Test

1. **Use the API** to fetch real equipment data:
   ```python
   from data import DofusAPIClient, CacheManager, EquipmentLoader
   api = DofusAPIClient()
   cache = CacheManager()
   loader = EquipmentLoader(cache=cache)
   raw = api.get_all_equipments(item_types=["ring", "hat"], min_level=50, max_level=100)
   equipments = loader.from_raw_batch(raw)
   ```

2. **Run the pipeline** with different configurations:
   ```python
   from processing import RuneMaster, ProcessingConfig
   config = ProcessingConfig(grouping_method="deterministic")
   master = RuneMaster(equipments, config=config)
   groups = master.run_deterministic()
   ```

3. **Record break observations** to calibrate the taux model:
   ```python
   cache.record_break_observation(
       item_id=12345,
       item_level=75,
       focus="Intelligence",
       runes_received={"Ine": 3},
       observed_density=0.15,
   )
   ```

4. **Compare configurations** using the harness:
   ```python
   from processing.harness import run_comparison
   rows = run_comparison(equipments, config, methods=("deterministic", "genetic"))
   ```

### How to Adapt

Based on your findings, you should:

1. **Update the valuation layer** if you discover that:
   - The rune density table needs correction
   - The focus formula needs adjustment
   - The set concentration penalty needs recalibration

2. **Update the exploration strategy** if you discover that:
   - The posterior taux model converges too slowly
   - The exploration bonus is too aggressive or too conservative
   - Certain item types are systematically over/under-explored

3. **Update the grouping strategy** if you discover that:
   - The compression metric misranks groups
   - The λ parameter needs adjustment
   - Certain graph structures are systematically missed

4. **Update the data collection** if you discover that:
   - The break_log schema is missing critical fields
   - The price_cache needs additional metadata
   - The capture module needs refinement

---

## Constraints

- **Do not break existing tests.** All changes must pass `uv run pytest -q`.
- **Do not fabricate data.** All conclusions must be grounded in actual API
  responses or recorded observations.
- **Do not skip the scientific method.** Every change must be motivated by a
  hypothesis, tested against data, and validated by results.
- **Do not optimize for a single metric.** Profit is the goal, but exploration
  value (information gain) is also valuable.
- **Do not ignore set membership.** It is a free, observable proxy for taux.

---

## Deliverables

After each iteration, you should produce:

1. **A hypothesis statement** — what you believed and why
2. **An experiment description** — what you tested and how
3. **A results summary** — what the data showed
4. **An analysis** — whether the hypothesis was confirmed or refuted
5. **A change recommendation** — what to implement, with code
6. **A negative result record** (if refuted) — what was learned

---

## Success Criteria

The iteration is successful when:

1. The system can **predict** which items are worth breaking with reasonable
   accuracy (measured by correlation between predicted and observed taux).
2. The system can **discover** high-taux items within a reasonable number of
   break observations (measured by cumulative regret).
3. The system can **adapt** to price changes and maintain profitability
   (measured by profit variance across price regimes).
4. The system can **explain** its recommendations in terms of the profit
   equation (measured by human interpretability).

---

## Notes

- The game mechanic is complex. Do not assume you understand it fully from
  the guide alone. Test your assumptions.
- The API is the ground truth. Do not assume the cached data is current.
- The taux is stochastic. Do not assume a single observation is conclusive.
- The market is dynamic. Do not assume prices are stable.
- The player's time is valuable. Do not recommend groups that take too long
  to craft or break.

---

## Starting Point

Begin by:

1. Reading the documentation in `docs/` to understand the full context.
2. Running the existing pipeline to see the current output.
3. Forming a hypothesis about what would most improve the system.
4. Designing an experiment to test that hypothesis.
5. Running the experiment and analyzing the results.
6. Implementing the change if the hypothesis is confirmed.
7. Recording the negative result if the hypothesis is refuted.
8. Repeating the loop with a new hypothesis.

The goal is not to find the perfect solution in one iteration. The goal is to
**learn something new with each iteration** and **improve the system
incrementally** based on what you learn.
