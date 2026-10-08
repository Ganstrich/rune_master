# Phase 0.3: Introduce GroupObjective Protocol

## Objective

Define the objective seam that makes the valuation swappable. Implement
`OverlapObjective` wrapping today's `quality_score` exactly. Give `marginal()`
a default implementation of `score(G + item) - score(G)`.

## Scope

- Extend `processing/valuation/objective.py` with the full protocol:
  ```python
  class GroupObjective(Protocol):
      def score(self, group: GroupCandidate) -> float: ...
      def marginal(self, group: GroupCandidate, item: Equipment) -> float: ...
  ```
- Implement `OverlapObjective` in `processing/valuation/overlap.py` wrapping
  `GroupQualityEvaluator` (already exists, verify it matches).
- Modify `processing/experts/base.py` — experts receive an objective in their
  constructor and use it for all scoring decisions.
- Modify `processing/orchestrator.py` — dispatch the objective to all experts.
- The default `marginal()` implementation is:
  ```python
  def marginal(self, group, item):
      return self.score(group.with_item(item)) - self.score(group)
  ```

## Acceptance Criteria

- `OverlapObjective` produces scores identical to the current `quality_score`.
- Experts can be instantiated with any `GroupObjective` implementation.
- The `marginal()` default is consistent with `score()` (verified by contract test).
- All existing tests pass.

## Ownership

- Primary: `processing/valuation/objective.py`, `processing/valuation/overlap.py`
- Modify: `processing/experts/base.py`, `processing/orchestrator.py`

## Validation

- Unit test: `OverlapObjective.score(group)` equals `GroupQualityEvaluator().evaluate(group).quality_score`.
- Contract test: `marginal(group, item)` equals `score(group.with_item(item)) - score(group)`.
- Integration test: run the deterministic method, verify output is unchanged.
- Run `uv run pytest -q` — all tests pass.

## Risks

- The `marginal()` default is O(n) per call (it constructs a new group). For
  greedy experts this is acceptable; for the genetic expert it may be slow.
  Optimize later only if profiling shows it matters.
- Experts currently access `group["quality_score"]` directly. These accesses
  must be replaced with `self.objective.score(group)`.
