# Phase 0.6: Replace Global Random with Injected Instances

## Objective

Replace module-level `random` usage with injected `Random(seed)` instances,
making reproducibility possible and safe under `ProcessPoolExecutor`.

## Scope

- `processing/random_group_builder.py`: replace `self.rng = random.Random(seed)`
  (already correct — verify) and remove any `random.` module-level calls.
- `processing/experts/genetic_expert.py`: uses `random.Random(config.random_seed)`
  — verify it does not fall back to module-level `random`.
- `processing/experts/random_expert.py`: verify same.
- `processing/tuner.py`: ensure each worker process creates its own `Random`
  instance from the config seed, not from global state.
- Add a contract test: two runs with the same seed produce identical output.

## Acceptance Criteria

- `grep -rn "^import random$" processing/` — only in modules that create
  `random.Random()` instances.
- Two consecutive runs with `--random-seed 42` produce identical group output.
- Tuner workers do not share global random state.
- All existing tests pass.

## Ownership

- Modify: `processing/random_group_builder.py`, `processing/experts/genetic_expert.py`,
  `processing/experts/random_expert.py`, `processing/tuner.py`
- Tests: `test/test_harness.py` (already tests reproducibility — extend)

## Validation

- Run the pipeline twice with the same seed, diff the output — identical.
- Run `uv run pytest -q` — all tests pass.

## Risks

- The `RandomGroupBuilder` currently creates `self.rng = random.Random(seed)`
  in `__init__`. If `seed` is `None`, this uses the global random state.
  Decide: should `None` mean "random each time" or "use a fixed default"?
  Currently it means "random each time" — preserve this behavior.
