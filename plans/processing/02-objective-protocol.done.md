# Group Objective Protocol

## Objective

Introduce a swappable objective so that "what makes a group good" is one
injectable component rather than logic embedded in four places.

## Depends On

[01-pure-blocks.done.md](01-pure-blocks.done.md)

## Scope

- Add `processing/valuation/objective.py`:

  ```python
  class GroupObjective(Protocol):
      def score(self, group: GroupCandidate) -> float: ...
      def marginal(self, group: GroupCandidate, item: Equipment) -> float: ...
  ```

- Provide a default `marginal()` of `score(group + item) - score(group)`.
- Add `valuation/overlap.py` implementing `OverlapObjective`, reproducing the
  current `quality_score` exactly, including weights and exclusion handling.
- Do not yet change any caller. This plan only creates the seam.

## Acceptance Criteria

- `OverlapObjective.score()` returns values identical to the current
  `GroupQualityEvaluator.evaluate().quality_score` for the same inputs.
- The default `marginal()` is correct for any objective without an override.
- Objectives are pure: no global state, no module-level `random`, all data
  sources injected.

## Ownership

- Primary: new `processing/valuation/`
- Tests: equivalence test against `GroupQualityEvaluator` over generated groups

## Validation

- Property test: for a sample of groups, `OverlapObjective.score()` equals the
  existing `quality_score` to within floating-point tolerance.
- Property test: `marginal(g, i)` equals `score(g + i) - score(g)` for any
  objective that overrides it.

## Risks

`marginal()` is not an optimisation convenience. The target objective is
non-additive over items, because taux decays in production volume and
acquisition cost applies to the union of resources
([../../docs/02-objective-model.md](../../docs/02-objective-model.md)). An
expert that assumes item values can be summed independently will be wrong once
`ProfitObjective` lands. Keeping the subtraction default makes that impossible
to get wrong by accident.
