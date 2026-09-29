# Next Steps - Evidence-Based Validation

The implementation is not declared production-ready by documentation alone. Each
claim below has a command or test that can confirm or reject it.

## Current Baseline

Completed on 2026-09-29:

- `uv run pytest -q` passes: 9 tests.
- `uv run python main.py --help` exposes deterministic, random, hybrid,
  committee, and genetic methods.
- `git diff --check` and `python3 -m compileall -q data processing main.py config.py`
  pass.
- Pytest imports are now configured through `pyproject.toml`.

Important correction: the current `ProcessingConfig` defaults are `hybrid`, 50
random groups, density ratio `3.0`, and no filtered-pool fallback. The older
claims that the default is deterministic, the ratio is `0.15`, or the count is
10 are not current behavior.

## Step 1: Keep the Test Gate Green

Run:

```bash
uv run pytest -q
python3 -m compileall -q data processing main.py config.py
git diff --check
```

Acceptance: all commands exit successfully. Any failure blocks later testing.

## Step 2: Add Offline Pipeline Coverage

Add fixture-based tests that do not call DofusAPI for:

- deterministic grouping and canonical group fields;
- random grouping with a fixed seed and no duplicate seed IDs;
- hybrid supplementation and its threshold behavior;
- density filtering, including the fallback path;
- visualization generation from synthetic groups.

Acceptance: tests are deterministic, run without network access, and assert
behavior rather than log messages.

## Step 3: Resolve the Configuration Contract

Choose and document the intended defaults. Until that decision is made, invoke
the method and parameters explicitly in validation commands:

```bash
uv run main.py --grouping-method deterministic --no-serve
uv run main.py --grouping-method random --random-groups 10 \
  --density-ratio 0.15 --no-serve
uv run main.py --grouping-method hybrid --random-groups 10 \
  --density-ratio 0.15 --no-serve
```

Acceptance: CLI values reach `ProcessingConfig`, invalid values fail clearly,
and the README, Makefile, and this file describe the same defaults.

## Step 4: Run Live Data Checks

Only after Steps 1-3 pass, run the three explicit modes against the API. Record
equipment count, active pool size, group count, elapsed time, and failures.

```bash
uv run main.py --grouping-method deterministic --no-serve
uv run main.py --grouping-method random --random-groups 10 \
  --density-ratio 0.15 --no-serve
uv run main.py --grouping-method hybrid --random-groups 10 \
  --density-ratio 0.15 --no-serve
```

Acceptance: the process exits zero, produces a non-empty report, and every
returned group has the canonical fields tested in Step 2. API failures are
reported separately from code failures.

Observed on 2026-09-29 with a warm cache:

- Deterministic: 272 equipment loaded, 34 groups generated.
- Random (`--random-groups 10`): 253 equipment in the filtered pool, 5 groups
  generated because only five sampled seeds had qualifying companions.
- Hybrid: 32 groups generated.
- Resource cache: 405 resources fetched on the initial run.

These results reject any assumption that requesting 10 random groups guarantees
10 results.

## Step 5: Verify the Report Surface

Serve the generated report and check the index plus one group page in a browser.
Confirm ingredient names and equipment links render without console errors.
Browser automation was used for the current check.

Acceptance: `index.html` and group pages load, contain non-placeholder data, and
the report directory is not accidentally committed as source.

## Step 6: Measure Before Calling It Ready

Record cached and uncached timings, filtered versus unfiltered pool sizes, group
counts, and coverage. Do not retain unsupported claims such as fixed API counts,
specific speedups, or 95% type coverage without a reproducible measurement.

## Open Decisions

- Should the public default remain `hybrid`, or become the deterministic mode
  described by the original quick start?
- Should hybrid results be de-duplicated before being returned?
- Should live API and browser checks become automated CI tests?

## Status

- Step 1 baseline commands: complete.
- Step 2 offline coverage: complete with 5 new tests.
- Step 3 CLI validation and random-seed support: complete.
- Step 3 default-method decision: documented as `hybrid`; the Makefile's
  explicit committee target remains a separate tuned workflow.
- Step 4 live data checks: complete, with the measured limitations above.
- Step 5 report verification: complete for the index, group pages, ingredient
  names, and equipment links.
- Step 6 measurement remains a gate for a production-readiness claim.