# Experts Consume An Injected Objective

## Objective

Make every expert a pure search strategy that optimises whatever objective it is
given, so the objective can be swapped without rewriting the experts.

## Depends On

[02-objective-protocol.done.md](02-objective-protocol.done.md),
[03-acceptance-policy.done.md](03-acceptance-policy.done.md)

## Scope

- Change the expert constructor to receive `(blocks, policy, objective)`.
- Remove `evaluate_group()` from `experts/base.py`; the objective replaces it.
- Replace each expert's private notion of quality with `objective.score()` or
  `objective.marginal()`:
  - `random_group_builder.find_companions` currently sorts by shared-count with
    the seed. Replace with greedy selection on `objective.marginal()`.
  - `genetic_expert._calculate_individual_fitness` currently instantiates
    `GroupQualityEvaluator` inline. Use the injected objective.
  - `genetic_expert` mutation `add` and `_create_graph_individual` growth use
    `objective.marginal()` instead of summed edge weight.
- Move the genetic expert's five constructor hyperparameters into
  `ProcessingConfig` so all experts instantiate uniformly.
- Remove the unused `precomputed_graph` and `precomputed_resources` parameters
  from any expert that ignores them, or document the contract if retained.

## Acceptance Criteria

- No expert imports `GroupQualityEvaluator` or any concrete objective.
- No expert contains a threshold comparison; all admissibility goes through
  policy.
- Swapping `OverlapObjective` for another objective requires no expert edits.
- `expert_name` and `selection_method` metadata are unchanged.

## Ownership

- Primary: `processing/experts/`, `processing/random_group_builder.py`
- Config: `processing/config_dataclass.py`
- Tests: existing expert contract tests, plus a test that injects a stub
  objective and asserts the experts honour it

## Validation

- Inject a stub objective returning a constant and assert every expert's ranking
  becomes arbitrary rather than overlap-driven. This proves no hidden coupling
  remains.
- Compare output on a fixed seed against the previous implementation; differences
  should be confined to the random builder's companion order.

## Risks

Companion selection in the random builder currently produces star topologies:
candidates are compared only to the seed, never to each other, so the shopping
list grows linearly with group size. Switching to `marginal()` fixes this but
will change random-expert output substantially. This is the intended correction
of Failing 3 in
[../../docs/03-current-state-audit.md](../../docs/03-current-state-audit.md).
