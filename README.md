# RuneMaster

RuneMaster is a local Python CLI that discovers groups of Dofus equipment whose
recipes share resources. It fetches equipment from DofusDB's public API, builds
resource-similarity graphs, runs one of several grouping strategies, aggregates
the ingredients required by each group, and writes a static HTML report.

The project is an optimization and analysis tool. It does not calculate market
prices, place orders, automate crafting, or expose a REST API.

## Current Scope

With the checked-in defaults, RuneMaster processes:

- Dofus 3 data in French from `https://api.dofusdu.de`;
- rings, amulets, hats, and cloaks;
- equipment from level 50 through 100;
- recipe entries whose subtype is `resources`;
- local output in `visualizations/`;
- a SQLite cache in `resource_cache.db`.

These API-level defaults live in `config.py`. Processing and grouping defaults
live in `processing/config_dataclass.py`.

## Requirements

- Python 3.12 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Network access to DofusDB for live pipeline runs

The core dependencies are NetworkX, python-louvain, NumPy, Requests, and tqdm.

## Quick Start

```bash
uv sync

# Run the default hybrid pipeline, generate reports, and open a local server.
uv run main.py

# Generate reports without keeping a server process open.
uv run main.py --no-serve

# Serve previously generated reports only.
uv run serve.py
```

Reports are written to `visualizations/index.html`. The built-in server binds to
`127.0.0.1:8000`, serves static files only, and opens the report in the default
browser. Use `uv run serve.py PORT` to choose another port for the standalone
server.

## Pipeline

1. **Fetch equipment**: `DofusAPIClient` requests paginated equipment records
     using the configured game, language, level range, and item types.
2. **Load models**: loaders convert API dictionaries into `Equipment`,
     `EquipmentStat`, and `ResourceRequirement` dataclasses and calculate stat
     weights.
3. **Populate the cache**: recipe resources are fetched individually when
     missing and stored in SQLite so reports can show resource names and images.
4. **Discover groups**: the selected expert builds groups using graph,
     stochastic, genetic, or committee logic.
5. **Measure groups**: recipe reuse, pairwise cohesion, quantity concentration,
    average stat density, and total ingredients are calculated canonically.
6. **Generate reports**: an index and one page per group are written as static
     HTML with copied CSS and JavaScript assets.

Sharing efficiency is the fraction of distinct recipe resources that occur in
at least two equipment recipes in a group. Configured excluded resource IDs do
not count as shared resources.

The primary item-only quality score combines resource-type reuse, mean pairwise
recipe Jaccard similarity, the fraction of overlapping equipment pairs, and the
quantity associated with reused resources. Algorithm summaries separately
report unique equipment coverage and duplicate assignments. These are heuristic
shortlist metrics, not estimates of profit or material savings.

## Grouping Methods

The RuneMaster pipeline supports six grouping strategies, each with distinct trade-offs between speed and result quality:

| Method | Speed | Quality | Best For |
| --- | --- | --- | --- |
| `deterministic` | ⚡⚡⚡ Very Fast | Good | Quick iterations, graph-only analysis |
| `random` | ⚡⚡ Fast | Fair | Solution space exploration |
| `hybrid` | ⚡⚡ Fast | Good | Balanced approach with deterministic fallback |
| `committee` | ⚡⚡ Fast | ⭐ Very Good | Fast multi-expert consensus |
| `genetic` | ⚡ Slower | ⭐ Very Good | Focused evolutionary search |
| `evolutionary_committee` | 🐢 Slowest | ⭐⭐⭐ Excellent | **Best overall results (default)** |

### Detailed Descriptions

- **`deterministic`**: Builds a Jaccard similarity graph and maps Louvain, BiLouvain, or connected-component communities into groups. Fast and reproducible. Works well for equipment with clear sharing patterns.

- **`random`**: Applies density filtering, samples unique seed equipment, and finds compatible companions. Explores the solution space stochastically. A requested group count is a target, not a guarantee.

- **`hybrid`**: Runs deterministic grouping first and supplements it with random groups only when the deterministic result is below a threshold. Balances determinism with fallback coverage.

- **`committee`**: Runs deterministic, random, and genetic experts in parallel, scores their proposals using the canonical objective, and removes groups whose equipment overlap exceeds the configured threshold. Individual expert failures are reported but do not block other experts. Single pass, fast.

- **`genetic`**: Evolves populations of candidate group sets using tournament selection, crossover, mutation, elitism, and stagnation-based early stopping. Single expert, focused optimization on group quality.

- **`evolutionary_committee`** (new, default): Combines the committee approach with multi-round portfolio evolution. Starts with expert proposals, then evolves them across 5 rounds (configurable), preserving elite candidates and injecting diversity through cold starts. Each round applies intelligent portfolio operators (add/remove equipment, split/merge groups, etc.). Produces the highest-quality portfolios by optimizing for overall coverage, overlap penalties, and balance—not just summing isolated group scores. **Recommended for best results.**

### When to Use Each Method

- **Need results now?** Use `hybrid` or `committee` (~seconds)
- **Quick dev iteration?** Use `deterministic` (~milliseconds)
- **Want the best groups?** Use `evolutionary_committee` (~minutes)
- **Exploring solutions?** Use `random` to see different possibilities
- **Single-expert deep dive?** Use `genetic` for focused evolution

### Default Behavior

The default grouping method is `evolutionary_committee`, which delivers the best portfolio quality. You can run it via:

```bash
make compute                                    # Evolutionary committee (best)
make method METHOD=committee                    # Fast multi-expert
make method METHOD=deterministic                # Fastest
```

The default method is configured in `processing/config_dataclass.py` and can be overridden via CLI:

```bash
uv run main.py --grouping-method deterministic
uv run main.py --grouping-method evolutionary_committee
```

## Processing Defaults

The authoritative defaults are defined by `ProcessingConfig`:

For the authoritative end-to-end specification of group construction,
method-specific parameter behavior, filtering, metrics, schemas, ensemble
selection, and tuning, see
[processing/PROCESSING.md](processing/PROCESSING.md). Other documentation gives
only a user-level summary and defers to that specification when details differ.

| Setting | Default |
| --- | ---: |
| Jaccard threshold | `0.3` |
| Minimum shared resources per graph edge | `1` |
| Minimum graph component size | `2` |
| Community algorithm | `louvain` |
| Group size | `2` to `18` |
| Minimum shared resources per group | `3` |
| Minimum sharing efficiency | `0.15` |
| Minimum item-only quality | `0.0` |
| Density filtering | enabled |
| Density/level ratio | `3.0` |
| Fall back to the unfiltered pool | disabled |
| Random group target | `50` |
| Committee duplicate-overlap threshold | `0.7` |

Density filtering keeps equipment where `stat_weight >= level * ratio`. It is
used by the random expert; deterministic graph grouping uses the loaded pool.

## CLI

```text
--grouping-method {deterministic,random,hybrid,committee,genetic}
--random-groups N       Positive target number of random groups
--density-ratio R       Non-negative density/level threshold
--random-seed N         Seed for reproducible random grouping
--tune                  Grid-search graph ratio and minimum shared resources
--no-serve              Generate reports without starting the HTTP server
--job-levels JOB:LEVEL[,...]   Crafting job levels, e.g. 'forgeron:120,bijoutier:80'
--no-job-filter         Ignore configured job levels and keep the full pool
```

Examples:

```bash
uv run main.py --grouping-method deterministic --no-serve
uv run main.py --grouping-method random --random-groups 10 --random-seed 42 --no-serve
uv run main.py --grouping-method committee --tune --no-serve
uv run main.py --job-levels "forgeron:120,bijoutier:80" --no-serve
```

`--tune` searches Jaccard thresholds `0.15`, `0.2`, `0.25`, and `0.3` against
minimum shared-resource counts `2`, `3`, and `4`. It scores assignment-weighted
group quality and unique equipment coverage while penalizing repeated equipment
assignments. It is a narrow, seeded heuristic search, not a trained model or a
general optimizer for every configuration field.

## Job-Level Filtering

Crafting an item needs a minimum job level, so a group you cannot craft is
useless. Configure your job levels and RuneMaster keeps only the equipment
you can actually craft — every expert, the policy, and the report then work
on that pool.

An item is kept when `job_levels[job] >= item_level`, where the job is the
one that crafts its type:

| Job | Item types |
| --- | --- |
| `cordonnier` | boots, belt |
| `bijoutier` | ring, amulet |
| `tailleur` | hat, cloak |
| `forgeron` | sword, hammer, dagger, axe, shovel, lance, scythe |
| `sculpteur` | staff, wand, bow |
| `faconneur` | shield |

Items whose type or job is unconfigured are kept — a new item type never
silently disappears, and a partial configuration is not destructive.

**Persistent config.** Copy `player_config.example.json` to
`player_config.json` in the project root and fill in your levels:

```json
{
  "job_levels": {
    "forgeron": 120,
    "bijoutier": 80
  }
}
```

Filtering stays off until at least one job level is present, so an empty or
missing file changes nothing.

**Per-run override.** `--job-levels` replaces the file value for the jobs it
names; `--no-job-filter` ignores all levels for one run. The effective levels
and the kept/filtered counts are printed and recorded in the report's run
manifest.

The pipeline prints a per-job breakdown of what was dropped:

```text
🔧 JOB-LEVEL FILTER
   forgeron     level 100: 252 items filtered
   kept                : 2606 items craftable
```

Equivalent Make targets include `make sync`, `make dev`, `make compute`,
`make tune`, `make method METHOD=genetic`, and `make serve`. Note that
`make compute` explicitly selects committee mode with tuning; it is not the same
as the default hybrid run.

## Python API

The processing layer can be used directly after constructing `Equipment`
objects:

```python
from processing import ProcessingConfig, RuneMaster

config = ProcessingConfig(
        grouping_method="deterministic",
        graph_min_shared_ratio=0.3,
        group_min_shared_resources=3,
)

master = RuneMaster(equipments, config=config)
groups = master.run_deterministic()
summary = master.get_summary()
```

`RuneMaster.run_all()` is a backward-compatible alias for deterministic
grouping. It does not dispatch from `config.grouping_method`; the CLI performs
that dispatch explicitly.

## Reports

The report generator creates:

- `visualizations/index.html` with group counts, average metrics, equipment
    previews, and links to detail pages;
- `visualizations/group_NNN.html` with group metrics, equipment images and stat
    weights, aggregated ingredient totals, and per-equipment quantities;
- `visualizations/static/` containing the CSS and JavaScript required by the
    generated pages.

Equipment and resource names can be clicked to copy them. The report is static:
changing parameters requires rerunning the pipeline and refreshing the page.
Generated output is ignored by Git. The generator overwrites current pages but
does not remove old higher-numbered group pages from earlier runs.

## Architecture

```text
config.py                 API query and cache defaults
main.py                   CLI, live data loading, dispatch, report generation
serve.py                  Standalone loopback static-file server
models/                   Equipment, resource, recipe, and shared data types
data/                     HTTP client, SQLite cache, and API-to-model loaders
processing/               Graphs, metrics, filters, grouping experts, and tuner
processing/job_filter.py  Craftability filter by player job levels
processing/experts/       Deterministic, random, and genetic expert adapters
visualization/            Static HTML generator and source assets
test/                     Offline contract and group-structure tests
plans/                    Reserved for the next feature plan after target definition
```

The SQLite cache contains resource API payloads, equipment effects, and computed
stat weights. It uses WAL mode and commits writes immediately. Delete
`resource_cache.db`, `resource_cache.db-wal`, and `resource_cache.db-shm` to
force a cold cache rebuild.

## Testing

```bash
uv run pytest -q
python3 -m compileall -q data processing main.py config.py test visualization
git diff --check
```

The current suite is offline and covers canonical group fields, random-seed
reproducibility, density-filter fallback, deterministic grouping, hybrid
supplementation, and basic report generation. It does not provide a published
coverage percentage, benchmark suite, or automated live-API test.

## Known Limitations

- Live runs depend on the availability and response shape of a third-party API.
- The server is local, unauthenticated, single-process, and static; there are no
    REST endpoints or live recomputation controls.
- Random grouping can return fewer groups than requested when sampled seeds do
    not have enough qualifying companions.
- Hybrid concatenates deterministic and random results without de-duplicating
    them; overlap de-duplication is specific to committee mode.
- Performance varies with API latency, cache warmth, configuration, and data
    volume. No fixed runtime or speedup is claimed.
- Type hints are present throughout much of the project, but no static type
    checker or measured type-coverage target is configured.
- `capture/debug_capture.py` and `capture/README.md` refer to capture service
    modules that are not present. The optional `capture` dependencies are declared,
    but the capture/OCR workflow is not currently runnable.

## Project Status

The core grouping and static-report workflow is implemented and covered by a
small offline test suite. Treat RuneMaster as a local analysis tool under active
validation, not as a production web service. See `NEXT_STEPS.md` for recorded
live checks, validation gates, and open product decisions.
