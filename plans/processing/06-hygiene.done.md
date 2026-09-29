# Dead Code And Randomness Hygiene

## Objective

Remove code that does nothing, code that is wrong and unused, and the global
random state that makes reproducibility claims false.

## Depends On

Nothing. Can run in parallel with any Phase 1 plan.

## Scope

Removals:

- `processing/resource_optimizer.py` (empty file) and the
  `use_resource_optimizer` config field, which nothing reads.
- `CommunityDetector.calculate_bulk_efficiency`, which is unreferenced **and**
  incorrect: it uses `set.intersection(*all_resources)`, meaning resources
  present in *every* item, where the specification defines shared as used by two
  or more.
- The `api_client` parameter threaded through roughly eight signatures and
  discarded with `del api_client` on arrival.

Fixes:

- Replace module-level `random.seed()` and `random.choice()` in
  `random_group_builder.py` and `genetic_expert.py` with an injected
  `random.Random(seed)` instance.
- Correct the stale docstring on `_calculate_individual_fitness`, which claims
  "Fitness = Sum(group_sharing_efficiency)" while the code sums `quality_score`.
- Remove the unused `resource_sets` parameter from
  `_calculate_individual_fitness`.
- Make `config` non-optional in `_calculate_individual_fitness`; it is typed
  `Optional[...] = None` but dereferenced unguarded, so `None` crashes rather
  than defaulting.
- Invert the `config_dataclass.py` to `quality_metrics.py` import so config does
  not depend on an algorithm module.

## Acceptance Criteria

- No module-level `random` calls remain in `processing/`.
- Two runs with the same seed produce identical output, including under the
  tuner's `ProcessPoolExecutor`.
- No signature accepts a parameter it does not use.
- All existing tests pass.

## Ownership

- Primary: `processing/random_group_builder.py`,
  `processing/experts/genetic_expert.py`, `processing/community_detector.py`,
  `processing/config_dataclass.py`
- Deleted: `processing/resource_optimizer.py`

## Validation

- Run the same seed twice under `deterministic`, `random`, `genetic`, and
  `committee`; assert identical group output.
- Run the tuner and assert worker results are reproducible.

## Risks

Seeding currently happens at module level, so experts sharing a process can
influence each other's stream. Injecting instances will change output for a
given seed even though it is strictly more correct. Record this as an expected,
one-time difference.
