# RuneMaster — Repository Summary for LLM Context

This file gives an LLM enough context to write prompts that guide a code assistant working on RuneMaster. It covers the domain, architecture, data models, pipeline, configuration, grouping methods, testing, and current project state.

---

## 1. What RuneMaster Is

RuneMaster is a local Python CLI that discovers groups of Dofus 3 equipment whose crafting recipes share resources. It fetches equipment data from DofusDB's public API, builds resource-similarity graphs, runs one of several grouping strategies, aggregates the ingredients required by each group, and writes a static HTML report.

**The ultimate goal** is to maximize profit from a craft-break-sell loop:
1. Buy crafting resources on the market.
2. Craft a set of different equipment items.
3. Break those items in the concasseur to obtain runes.
4. Sell the runes on the market.

The profit equation is:

```
Profit = sum_i(n_i * E[tau_i(n_i)] * D_i(f_i) * rho_fi) - sum_i(n_i * c_i) - lambda * |union R_i| - impact - gamma * set_concentration(G)
```

Where:
- G = group of items to craft
- n_i = how many of item i to produce
- tau_i(n_i) = break rate (taux) of item i, decaying in n_i
- D_i(f_i) = break density under focus f_i (from the rune density table)
- rho_fi = market price per unit density of rune f_i
- c_i = craft cost of item i at spot resource prices
- lambda = fixed acquisition cost per distinct resource
- union R_i = the union of all resources needed
- impact = order-book walk penalty for large orders
- gamma * set_concentration(G) = penalty for crafting items from the same panoplie

**The grouping problem** is the sub-problem of choosing G: a set of items whose recipes share resources, so the shopping list is short and cheap, while the items are diverse enough to discover high-taux opportunities.

**The discovery problem** is the meta-problem: tau_i is unknowable before breaking, so the system must explore (break many different item types) while exploiting (break known high-taux items while their taux holds).

**The end goal is NOT "maximize recipe overlap."** Overlap is the mechanism that makes exploration affordable. The goal is profit.

---

## 2. Tech Stack

- **Language:** Python 3.12+
- **Package manager:** uv
- **Core dependencies:** networkx, python-louvain, numpy, requests, tqdm
- **Dev dependencies:** pytest
- **Optional (capture):** mss, pynput, easyocr, opencv-python (not currently runnable)
- **Data storage:** SQLite (WAL mode) for resource cache
- **Output:** Static HTML with CSS/JS assets

---

## 3. Repository Layout

```
rune_master/
  config.py                     API-level config (game, language, levels, item types, cache file)
  main.py                       CLI entry point, dispatch, report generation, server startup
  serve.py                      Standalone loopback static-file server
  models/
    equipment.py                Equipment, EquipmentStat, ResourceRequirement dataclasses
    resource.py                 Resource data model
    recipe.py                   Recipe data model
    common.py                   Shared types (ImageURLs, ItemType, StatType)
    MODELS.md                   Data model documentation
  data/
    api_client.py               DofusDB HTTP client (paginated equipment, resources, set index)
    cache_manager.py            SQLite cache for resources, equipment effects, stat weights, set index
    loaders.py                  API-to-model loaders, stat weight calculation, density filtering
    DATA.md                     Data layer documentation
  processing/
    orchestrator.py            RuneMaster MoE coordinator and method dispatch
    config.py                  ProcessingConfig — all pipeline defaults and hyperparameters
    policy.py                  Group acceptance policy (size, line-item cap, unit budget, set concentration)
    graph/
      graph_builder.py         Jaccard similarity graph construction
      community_detector.py    Louvain/BiLouvain/connected-component community detection
      group_mapper.py          Maps communities to groups, applies policy filters
    experts/
      base.py                  GroupingExpert ABC (the interface for all experts)
      graph_expert.py          Graph-based deterministic grouping
      random_expert.py         Stochastic random grouping
      random_group_builder.py  Seed-and-companion proposal construction
      greedy_expert.py         Objective-driven greedy grouping (default)
    filters/
      equipment_filter.py      Density filtering and panoplie set exclusion
      job_filter.py            Craftability filter by player job levels
    metrics/
      quality_metrics.py       Group/portfolio quality scoring (sharing efficiency, Jaccard, compression)
      group_metrics.py         Canonical group schema builder (GroupMetrics.build_group_dict)
      break_log.py             Observed-taux and rune-density helpers
      selection.py             ProcessingReporter (run summary)
    valuation/
      objective.py             GroupCandidate and GroupObjective protocol
      overlap.py               OverlapObjective (current objective)
      economic.py              ProfitObjective and FlatTauxModel
      focus.py                 Break-density and focus formulas
      density.py               RUNE_DENSITY table and stat-name resolution
      taux.py                  PosteriorTauxModel
      prices.py                PriceSource contracts
      exploration.py           Break-exploration ranking
      stat_calculator.py       Stat weight calculation (feeds into density)
    blocks/
      recipes.py               Recipe normalization helpers
      shopping_list.py         Shopping-list arithmetic
      similarity.py            Jaccard similarity
    tools/
      harness.py               Offline method comparison
      tuner.py                 Grid-search parameter tuner
    PROCESSING.md              Authoritative end-to-end specification of group construction
  analysis/
    challenge_metrics.py       API-only challenge metrics (not imported by the runtime pipeline)
  visualization/
    html_generator.py           Static HTML report generator (index + per-group pages)
    static/                     CSS and JS assets
  test/                         Offline contract and group-structure tests
  docs/
    00-goal-statement-and-clean-slate-todo.md   Entry point: goal, challenges, 6-phase plan
    01-domain-model.md                          Game mechanic (rune density, focus, taux)
    02-objective-model.md                       Profit equation
    03-current-state-audit.md                   Implementation weaknesses
    04-target-architecture.md                   Target module layout and design principles
    05-roadmap.md                               Staged plan and open decisions
  plans/                        Feature plans (explainable shortlist, run manifest, filtering, etc.)
  .github/
    instructions/               Copilot and Python instruction files
    agents/RuneWizard.agent.md  Agent configuration
  .clinerules                   Cursor rules
  GROUPING_METHODS.md           Detailed grouping method comparison
  NEXT_STEPS.md                 Current product status and prioritized roadmap
  Makefile                      Build targets (sync, serve, compute, evolve, tune, method, clean)
  pyproject.toml                Project metadata and dependencies
  requirements.txt              Pip-compatible dependency list
```

---

## 4. Data Models

### Equipment (models/equipment.py)
```python
@dataclass(frozen=False)
class Equipment:
    ankama_id: int
    type: ItemType          # "ring", "hat", "boots", "belt", "amulet", "cloak", etc.
    level: int
    name: str
    effects: List[EquipmentStat]
    stat_weight: Optional[float]   # Calculated from effects
    recipe: List[ResourceRequirement]
    image_urls: Optional[ImageURLs]
    set_id: Optional[int]          # None = no panoplie membership
```

### EquipmentStat (models/equipment.py)
```python
class EquipmentStat:
    stat_type: StatType    # dict with 'id' and 'name'
    int_minimum: int
    int_maximum: int
    ignore_int_min: bool
    ignore_int_max: bool
    formatted: str
```

### ResourceRequirement (models/equipment.py)
```python
@dataclass(frozen=True)
class ResourceRequirement:
    resource_id: int
    quantity: int
```

---

## 5. Pipeline Flow

1. **Fetch equipment:** DofusAPIClient requests paginated equipment records using configured game, language, level range, and item types.
2. **Load models:** Loaders convert API dictionaries into Equipment, EquipmentStat, and ResourceRequirement dataclasses and calculate stat weights.
3. **Populate cache:** Recipe resources are fetched individually when missing and stored in SQLite.
4. **Discover groups:** The selected expert builds groups using graph, stochastic, or objective-driven greedy logic.
5. **Measure groups:** Recipe reuse, pairwise cohesion, quantity concentration, average stat density, and total ingredients are calculated canonically.
6. **Generate reports:** An index and one page per group are written as static HTML with copied CSS and JavaScript assets.

---

## 6. Grouping Methods

| Method | Speed | Quality | Best For |
| --- | --- | --- | --- |
| `deterministic` | Very Fast | Good | Quick iterations, graph-only analysis |
| `random` | Fast | Fair | Solution space exploration |
| `hybrid` | Fast | Good | Balanced approach with deterministic fallback |
| `greedy` | Fast | Very Good | Objective-driven greedy grouping (default) |
| `survey` | Slowest | Diagnostic | Runs all experts, tags groups with origin |

**Default:** `greedy` (in ProcessingConfig). CLI can override with `--grouping-method`.

**Make targets:**
- `make compute` — runs survey mode (all experts)
- `make evolve` — runs greedy (default)
- `make method METHOD=greedy` — runs specific method
- `make tune` — runs with parameter tuning

**Removed methods (2026-10-10):** `committee`, `genetic`, `evolutionary_committee`, `baseline` — measured as dominated by greedy (see `plans/phase1-decision.md`). Their code and config fields have been deleted.

---

## 7. Configuration

### API-Level (config.py)
- `GAME = "dofus3"`
- `LANGUAGE = "fr"`
- `MIN_LEVEL = 1`, `MAX_LEVEL = 200`
- `ITEM_TYPES = ALL_CRAFTABLE_TYPES` (18 craftable types: ring, hat, boots, belt, amulet, cloak, shield, sword, staff, hammer, wand, dagger, bow, axe, shovel, lance, scythe)
- `CACHE_FILE = "resource_cache.db"`
- `OUTPUT_PREFIX = "crafting_groups"`

### Processing-Level (processing/config.py — ProcessingConfig)
Key defaults:
- `graph_min_shared_ratio = 0.15` — Jaccard threshold for graph edges
- `graph_min_shared_count = 1` — Min absolute shared resources for edge
- `group_min_size = 2`, `group_max_size = 12`
- `group_min_shared_resources = 3`
- `group_efficiency_threshold = 0.15`
- `group_max_set_share = 0.5` — Max share from one panoplie
- `max_line_items = 32` — Cap on distinct resources per group
- `max_total_units = 2000` — Carry capacity cap
- `excluded_resource_ids = {14635}` — Don't count toward sharing
- `use_density_filtering = True`
- `equipment_density_level_ratio = 2.0`
- `grouping_method = "greedy"`
- `random_group_count = 50`
- `dedup_overlap_threshold = 0.7`

---

## 8. CLI Interface

```bash
uv run main.py [options]

Options:
  --grouping-method {deterministic,random,hybrid,greedy,survey}
  --random-groups N       Target number of random groups
  --density-ratio R       Density/level threshold
  --random-seed N         Seed for reproducible random grouping
  --min-level N           Minimum item level (default: 1)
  --max-level N           Maximum item level (default: 100)
  --item-types TYPES      Comma-separated item types
  --tune                  Grid-search graph ratio and minimum shared resources
  --no-serve              Generate reports without starting the HTTP server
```

---

## 9. Testing and Verification

**Working gate (must stay green):**
```bash
uv run pytest -q
python3 -m compileall -q data processing main.py config.py
git diff --check
```

**Test suite:** Offline tests covering canonical group fields, random-seed reproducibility, density-filter fallback, deterministic grouping, hybrid supplementation, and basic report generation. No live-API test or coverage percentage.

**Python API usage:**
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

---

## 10. Design Principles and Invariants

1. **Policy vs. Objective separation:** `policy.py` owns hard constraints (size, line-item cap, unit budget, set concentration). `valuation/` owns "what is a group worth" (reuse, compactness, revenue, cost). These must stay strictly separate.

2. **Objective seam:** `GroupObjective` protocol with `score(group)` and `marginal(group, item)`. The default `marginal()` is `score(group + item) - score(group)`. This makes the objective swappable without rewriting experts.

3. **Canonical group schema:** `GroupMetrics.build_group_dict()` is the single constructor of the canonical group schema.

4. **PROCESSING.md is authoritative:** Where other docs disagree about current behavior, `processing/PROCESSING.md` is right.

5. **No global state:** Objectives are pure functions of a group plus injected data sources. No module-level `random`.

6. **Experts receive (blocks, policy, objective)** and return candidate groups. They own no formulas.

7. **Set concentration matters:** Items from the same panoplie are heavily broken by other players and have low taux. Groups dominated by a single panoplie are poor exploration vehicles.

---

## 11. Current State and Roadmap

### What's Working
- Core grouping and static-report workflow is implemented
- 15 offline tests pass
- All 8 grouping methods are exposed via CLI
- Live API integration with DofusDB
- SQLite caching with WAL mode
- Static HTML reports with group metrics and ingredient breakdowns

### Prioritized Roadmap (from NEXT_STEPS.md)
1. **Explainable Shortlist** — Make ranking visible through rank labels and evidence on index cards
2. **Reproducible Run Manifest** — Record query scope, config, seed, cache context, timestamp with every report
3. **Report Filtering and Sorting** — Filter and reorder groups without rerunning the pipeline
4. **Combined Shopping List** — Aggregate ingredients across selected groups
5. **Configurable Analysis Scope** — Expose levels, item types, language, game as CLI options
6. **Cache and API Resilience** — Retries, partial-data warnings, cache freshness visibility

### Longer-Term Vision (from docs/00)
- **Phase 0:** Foundation — extract similarity, shopping list, objective protocol, policy, delete dead code, inject random instances
- **Phase 1:** Valuation Layer — rune density, focus formulas, compression metric, line-item constraints, set concentration gates
- **Phase 2:** Data Collection — break_log table, price_cache table, FlatTauxModel
- **Phase 3:** Profit Objective — ProfitObjective combining revenue, cost, acquisition, exploration
- **Phase 4:** Exploration Strategy — PosteriorTauxModel, exploration shortlist
- **Phase 5:** Solver Improvement — greedy baseline, ILP Set Cover, benchmark suite
- **Phase 6:** Capture Integration — OCR price capture, break result capture

---

## 12. Known Limitations

- Live runs depend on DofusDB API availability and response shape
- Server is local, unauthenticated, single-process, static — no REST endpoints
- Random grouping can return fewer groups than requested
- Hybrid concatenates deterministic and random results without de-duplication
- No static type checker configured
- Capture/OCR workflow is not currently runnable (modules not present)
- No market-price model, profit forecast, crafting automation, or deployment target
- The system optimizes recipe overlap (a proxy) rather than profit (the true objective) — this is a fundamental epistemic limitation until break_log data exists

---

## 13. Key Files to Know When Writing Prompts

| Task | Key Files |
| --- | --- |
| Change grouping behavior | processing/config.py, processing/orchestrator.py, processing/experts/ |
| Change quality scoring | processing/metrics/quality_metrics.py, processing/metrics/group_metrics.py |
| Change group acceptance | processing/policy.py |
| Change API/data fetching | data/api_client.py, data/loaders.py, data/cache_manager.py, config.py |
| Change data models | models/equipment.py, models/common.py |
| Change CLI | main.py |
| Change reports | visualization/html_generator.py |
| Change tests | test/ |
| Understand current behavior | processing/PROCESSING.md |
| Understand the goal | docs/00-goal-statement-and-clean-slate-todo.md |
| Understand the domain | docs/01-domain-model.md |
| Understand the objective | docs/02-objective-model.md |
| Understand weaknesses | docs/03-current-state-audit.md |
| Understand target architecture | docs/04-target-architecture.md |
| Understand roadmap | docs/05-roadmap.md, NEXT_STEPS.md |
