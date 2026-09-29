# Evolve Groups Under The Profit Objective

## Objective

When prices arrive, **evolve** the existing theory-built groups toward profit
rather than re-scoring them or rebuilding from scratch.

## Depends On

[22-profit-objective.md](22-profit-objective.md),
[04-experts-consume-objective.md](04-experts-consume-objective.md)

## Scope

- Warm-start the genetic expert: seed the initial population with Phase 1
  groups instead of random graph walks.
- Keep a fraction of the population randomly initialised, so the search can
  leave the neighbourhood of the theory groups.
- Run evolution with `ProfitObjective` injected. No expert code changes are
  required; this is the payoff of
  [04-experts-consume-objective.md](04-experts-consume-objective.md).
- Add a re-evaluation entry point that takes a stored portfolio and evolves it
  against current prices.
- Record provenance on each group: theory-only, evolved, or newly discovered.

## Why Evolve Rather Than Re-Rank

Re-scoring theory groups keeps the search inside a candidate set that was chosen
for recipe compactness. The profit-optimal group is a *different* group: it may
drop a compact-but-worthless item or add a costly one whose rune yield pays for
itself. Re-ranking a fixed candidate set cannot find either.

Evolution is the right mechanism because the theory groups are good starting
points — they are already cheap to buy — and the profit objective refines them
rather than replacing the reasoning that produced them.

## Acceptance Criteria

- Warm-started evolution reaches a higher profit score than both the unmodified
  theory groups and a cold-start run, given the same budget.
- Provenance is visible in reports.
- Re-evaluation is repeatable: same prices and same seed give the same result.
- Group membership changes relative to Phase 1 in a way that can be explained by
  price differences, not by search noise.

## Ownership

- Primary: `processing/experts/genetic_expert.py` initialisation,
  `processing/selection.py`
- Tests: warm-start versus cold-start comparison on fixed prices

## Validation

- Run theory-only, cold-start profit, and warm-start profit on identical data;
  report all three scores.
- Confirm that with uniform prices, evolution does not meaningfully disturb the
  theory groups. If it does, the objective or the search is unstable.

## Risks

Prices move, so an evolved portfolio decays. Record the price snapshot used, and
treat a portfolio as valid only against the prices it was evolved under. The
re-evaluation cadence is a user decision; do not cache evolved portfolios across
price updates without revalidating.
