# Next Steps

RuneMaster has a working local CLI and static report pipeline. This file is a
clean starting point for the next product phase; it intentionally contains no
commitment to the previously proposed API, configuration endpoint, filtering
workflow, or frontend form.

## Verified Baseline

Validated on 2026-09-29:

- `uv run pytest -q`: 14 tests pass.
- `uv run python main.py --help`: all five grouping methods are exposed.
- `python3 -m compileall -q data processing main.py config.py`: passes.
- `git diff --check`: passes.
- Live and browser checks have been performed, but are not automated.

Current product boundaries remain documented in `README.md`: local CLI, live
DofusDB dependency, SQLite cache, static HTML reports, and loopback-only
serving. There is no REST API, market-price model, crafting automation, or
production deployment target.

## Next Decision: Define the Product Target

Before creating another implementation plan, write a short product brief that
answers:

- Who is the primary crafter or analyst using RuneMaster?
- What decision should the tool help them make faster or better?
- What inputs, outputs, and evidence make that decision trustworthy?
- Which workflow must be excellent in the first feature slice?
- What is explicitly out of scope for this phase?

## Feature Slice Gate

For the first chosen feature, record:

- a baseline using the current CLI/report workflow;
- one measurable user-facing success signal;
- the owning module and smallest coherent change;
- offline tests and any required live validation;
- known data, performance, and reproducibility risks.

Do not add a plan until those points are clear. Do not describe a feature as
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