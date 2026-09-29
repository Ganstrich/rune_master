# Evolutionary Portfolio Search

## Objective

Turn the current genetic expert into a repeatable evolutionary search for the
best accepted, non-redundant portfolio of equipment groups. Experts should
propose candidate portfolios, receive feedback from the shared objective, and
iterate until the search budget is exhausted or improvement converges.

This is evolutionary optimization, not model training: no weights are learned
from historical runs. The search must remain useful with the current overlap
objective and must also accept a future price- or taux-aware objective.

## Depends On

[04-experts-consume-objective.done.md](04-experts-consume-objective.done.md),
[05-selection-module.done.md](05-selection-module.done.md),
[12-baseline-harness.done.md](12-baseline-harness.done.md)

[23-evolve-under-profit.done.md](23-evolve-under-profit.done.md) is compatible
with this plan and should reuse the same warm-start and provenance contracts.

## Current Gaps

- `GeneticGroupingExpert` evolves individuals internally, but the committee
  only runs each expert once and then performs greedy score-order deduplication.
- The genetic fitness function scores groups plus a local overlap penalty, not
  the final portfolio through the canonical portfolio evaluator.
- Candidate proposals are not retained as a searchable archive between rounds.
- The genetic entry point in `RuneMaster` must be restored as a real method
  before the evolutionary path can be selected reliably.
- The current tuner searches two graph thresholds only; it is not the
  evolutionary search loop described here.

## Scope

### 1. Define the evolutionary search state

Add an explicit internal representation for a candidate portfolio, containing:

- groups or equipment memberships;
- objective score and portfolio metrics;
- generation and parent provenance;
- a stable candidate fingerprint for deduplication;
- feasibility/admissibility status and rejection reason when applicable.

Keep this representation internal to processing. Existing group dictionaries
and report contracts remain the external API.

### 2. Evolve portfolios, not only isolated groups

The fitness function for a candidate portfolio must use the same portfolio
semantics as reporting and committee selection:

- group quality reward;
- unique equipment coverage;
- duplicate-assignment penalty;
- group overlap penalty;
- line-item and total-unit constraints.

A candidate that has excellent individual groups but poor portfolio coverage
must not outrank a balanced portfolio merely because its group scores sum higher.
The objective remains injected; the evolutionary engine must not import a
concrete valuation implementation.

### 3. Add proposal operators

Implement deterministic, seeded operators that preserve valid equipment
memberships where possible:

- add an equipment adjacent in the similarity graph;
- remove the weakest marginal equipment;
- swap one equipment for a graph neighbor;
- split an oversized group;
- merge compatible groups;
- move an equipment between groups;
- introduce a cold-start random portfolio for diversity.

Every operator must pass candidates through the shared acceptance policy before
final reporting. Invalid intermediate candidates may be scored as infeasible,
but must not silently become final groups.

### 4. Add iterative committee evolution

Extend the committee path with configurable rounds:

1. collect proposals from baseline, graph, random, and genetic experts;
2. normalize them into candidate portfolios;
3. score the whole candidate pool;
4. retain an elite set and a diverse set;
5. generate the next population through mutation, crossover, and cold starts;
6. repeat until the configured round limit or stagnation limit;
7. select the final non-overlapping portfolio through one canonical selector.

Expert failures remain isolated and visible in the expert report.

### 5. Support warm starts and provenance

Allow a stored portfolio or prior expert proposals to seed the initial
population. Preserve provenance values such as `theory`, `random`,
`evolved`, and `warm_started`, and record parent/generation metadata where it is
safe to expose it in diagnostics.

Warm starts must retain a configurable cold-start fraction so the search can
leave a poor local neighborhood.

### 6. Make behavior configurable and reproducible

Add configuration fields for the evolutionary layer, with conservative
 defaults:

- population size;
- evolution rounds/generations;
- elite count;
- mutation and crossover rates;
- cold-start fraction;
- archive size;
- diversity/fingerprint threshold;
- stagnation limit;
- tournament size;
- random seed.

Validate incompatible values at configuration boundaries. Use an injected
random generator or per-run seeded generator; do not depend on module-global
random state. The same input, objective, config, and seed must produce the same
final portfolio and diagnostics.

## Non-Goals

- No neural-network training or learned expert weights.
- No automatic tuning of every `ProcessingConfig` field in this plan.
- No market-price or taux model; those arrive through an injected objective.
- No persistence of an archive across runs until its serialization contract is
  specified. Warm-start input may be persisted groups, but not opaque internal
  state.

## Acceptance Criteria

- Genetic mode is callable directly from `RuneMaster` and the CLI.
- The evolutionary committee can improve or match the best initial portfolio
  under a fixed objective and seed; it must never return a lower-scoring result
  solely because additional rounds were enabled.
- Final portfolios satisfy the common acceptance policy and canonical
  deduplication rules.
- Identical input, objective, configuration, and seed produce identical group
  memberships, provenance, and scores.
- A non-additive portfolio objective changes selection when coverage or overlap
  changes, proving the engine is not summing isolated group scores.
- Warm-started search preserves at least one eligible seed unless the policy
  rejects it, while cold-start diversity remains configurable.
- Expert failures are reported without preventing other experts from producing
  a final result.
- Existing harness output remains stable when evolutionary rounds are disabled
  or when the legacy method is explicitly selected.

## Ownership

- Primary: `processing/experts/genetic_expert.py`, new evolutionary search
  module under `processing/`, `processing/selection.py`, and
  `processing/orchestrator.py`.
- Configuration: `processing/config_dataclass.py`.
- Diagnostics/reporting: `processing/selection.py` and visualization metadata.
- Tests: genetic expert, committee, selection, harness, determinism, and warm
  start tests.

## Validation

Add focused tests for:

- each mutation operator's membership and size invariants;
- portfolio fitness rewarding coverage and penalizing duplicate assignments;
- archive fingerprinting and diversity limits;
- fixed-seed repeatability;
- stagnation stopping and elite preservation;
- warm-start plus cold-start population composition;
- expert failure isolation;
- final policy and deduplication compliance;
- a fixed fixture where iterative evolution beats the initial population;
- harness comparison of baseline, one-shot genetic, and evolutionary
  committee modes.

Run the shared gate:

```bash
uv run pytest -q
python3 -m compileall -q data processing main.py config.py test visualization
git diff --check
```

Because this changes output, record before/after distributions for group size,
line-item count, equipment coverage, duplicate assignment rate, and portfolio
score on a fixed fixture and one cached real-data run.

## Risks And Decisions

- A portfolio-level search can collapse into one high-scoring group. Enforce
  diversity and coverage constraints explicitly rather than relying on an
  overlap penalty alone.
- Aggressive mutation can make results unstable. Prefer small valid edits and
  expose mutation rates in config.
- Objective changes can alter the meaning of "best". Store objective identity
  and relevant config in diagnostics so results remain explainable.
- Search budgets can multiply runtime in committee mode. Start with a bounded
  round count and measure runtime alongside quality in the harness.
- The existing group dictionary is mutable. Candidate evaluation should avoid
  mutating shared proposals or should clone them before attaching scores and
  provenance.
