# Next Steps

RuneMaster has a working local CLI and static report pipeline. This file is a
clean starting point for the next product phase; it intentionally contains no
commitment to the previously proposed API, configuration endpoint, filtering
workflow, or frontend form.

## Verified Baseline

Validated on 2026-09-29:

- `uv run pytest -q`: 15 tests pass.
- `uv run python main.py --help`: all five grouping methods are exposed.
- `python3 -m compileall -q data processing main.py config.py`: passes.
- `git diff --check`: passes.
- Live and browser checks have been performed, but are not automated.

Current product boundaries remain documented in `README.md`: local CLI, live
DofusDB dependency, SQLite cache, static HTML reports, and loopback-only
serving. There is no REST API, market-price model, crafting automation, or
production deployment target.

## Product Target

RuneMaster serves a Dofus crafter or crafting-focused analyst choosing which
equipment recipes to prepare together. It should make resource reuse visible
and reduce the time needed to select a small, defensible crafting shortlist.

Trustworthy evidence comes from the configured DofusDB equipment and recipes.
Reports show shared-resource count, sharing efficiency, group size, ingredient
totals, and average stat density. RuneMaster does not claim profit because it
has no market-price model.

The first workflow is: run the CLI, open the report index, inspect the strongest
recipe-sharing candidates, and open their ingredient breakdowns. Market prices,
profit forecasts, inventory, crafting automation, accounts, REST endpoints, and
deployment remain out of scope.

## Completed Slice

The crafting shortlist is implemented in the report generator. Groups are
ordered by sharing efficiency, shared-resource count, average density, and group
size, with stable ordering for complete ties. Offline tests and the working gate
are green.

The remaining usability gap is that the ranking is implicit: the report does
not yet explain why a group appears first.

## Prioritized Roadmap

### 1. Explainable Shortlist

Make the ranking visible through rank labels and concise evidence on each index
card. This is the next implementation slice because it improves user trust
without changing grouping behavior or introducing unsupported financial claims.

Plan: [plans/01-explainable-shortlist.md](plans/01-explainable-shortlist.md)

### 2. Reproducible Run Manifest

Record the query scope, grouping configuration, random seed, cache/data context,
and generation timestamp with every report.

Plan: [plans/02-run-manifest.md](plans/02-run-manifest.md)

## Notes for Later Expansion

These are deliberately sequenced after explainability and reproducibility.

### 3. Report Filtering and Sorting

Allow users to filter and reorder already-generated groups by level, group size,
efficiency, density, and method without rerunning the pipeline.

Plan: [plans/03-report-filtering.md](plans/03-report-filtering.md)

### 4. Combined Shopping List

Aggregate ingredients across selected groups to help plan several crafts while
preserving each group's individual breakdown.

Plan: [plans/04-combined-shopping-list.md](plans/04-combined-shopping-list.md)

### 5. Configurable Analysis Scope

Expose levels, item types, language, and game scope as explicit CLI options with
the same values recorded in the run manifest.

Plan: [plans/05-analysis-scope.md](plans/05-analysis-scope.md)

### 6. Cache and API Resilience

Improve retries, partial-data warnings, cache freshness visibility, and failure
reporting without hiding stale or incomplete source data.

Plan: [plans/06-cache-api-resilience.md](plans/06-cache-api-resilience.md)

## Feature Slice Gate

Every selected feature needs a baseline, one measurable user-facing success
signal, a named owning module, offline tests, required live or browser checks,
and documented data, performance, and reproducibility risks. A feature is not
implemented until source, tests, and executable behavior agree.

## Working Gate

Every feature change must keep this gate green:

```bash
uv run pytest -q
python3 -m compileall -q data processing main.py config.py
git diff --check
```

Keep live API measurements and browser verification separate from the offline
regression gate. Never promote measured local behavior into a production claim
without a reproducible test or observation.