# Phase 0 — Baseline (no code change)

Branch: `refactor/simplify-processing` (cut from `a5490c5`).
Reference artifacts (outside repo): `/tmp/baseline/`.

## Baseline numbers

- Full test suite: **156 passed** (`uv run pytest -q`), 0 failed, 1.94s.
- processing/ root files: **23** (22 modules + `__init__.py`).
- processing/ total LOC: **6058** (root 4389 + subpackages 1669).
- CLI smoke (deterministic):
  `uv run main.py --no-serve --grouping-method greedy --random-seed 0 --min-level 1 --max-level 40 --item-types ring,amulet`
  -> exit 0, **18 groups**, 20 HTML files, ~10s.
  Saved: `/tmp/baseline/cli_greedy.txt`, `/tmp/baseline/visualizations_greedy/`.
- Determinism verified: two runs byte-identical on every `group_*.html`,
  on the embedded `group-data` JSON and on the index group cards.
  Comparison tool: `/tmp/baseline/compare_vis.py`.

### CLI diff key
- Exact-match: each `group_NNN.html`; the `<script id="group-data">` block;
  the `<div class="groups-container">` cards.
- Ignored (non-deterministic or intentionally changed): `manifest.json`
  `run_id`/`generated_at`; index `Report <code>..</code>`.
- `manifest.json.processing_config` embeds the whole ProcessingConfig, so
  deleting legacy config fields WILL change the manifest. Expected; the
  deterministic group output is the behaviour contract.

## Import graph (repo-wide, excluding __pycache__)

```
blocks.recipes        <- blocks/__init__, blocks/shopping_list, experts/{baseline,greedy}_expert,
                         exploration, graph_builder, group_mapper, group_metrics,
                         random_group_builder, valuation/economic, analysis_sweep,
                         scripts/challenge_coverage_gap, test/test_processing_blocks
blocks.shopping_list  <- blocks/__init__, visualization/html_generator, test/test_processing_blocks
blocks.similarity     <- blocks/__init__, community_detector, graph_builder, quality_metrics,
                         selection, analysis_sweep, test/test_processing_blocks
break_log             <- break_log.py (root CLI), capture/break_ingestion, test/test_break_log
challenge_metrics     <- scripts/challenge_evaluate, test/test_challenge_metrics
community_detector    <- experts/graph_expert, processing/__init__, analysis_sweep
config_dataclass      <- broad (31 files incl. main.py via package, data/loaders, experts/*,
                         orchestrator, policy, harness, tuner, scripts, tests)
equipment_filter      <- orchestrator, scripts/challenge_*, test/{group_structure,metrics_revision,pipeline_contracts,refactor_snapshot}
evolutionary_fitness  <- processing/__init__, evolutionary_search_engine           [LEGACY]
evolutionary_operators<- processing/__init__, evolutionary_search_engine           [LEGACY]
evolutionary_search_engine <- processing/__init__, test/test_evolutionary_search   [LEGACY]
evolutionary_search_state  <- evolutionary_{fitness,operators,search_engine}, test_evolutionary_search [LEGACY]
experts.base          <- experts/{baseline,genetic,graph,greedy,random}_expert
experts.baseline_expert    <- NONE (ORPHAN)
experts.genetic_expert     <- test/test_warm_start                                 [LEGACY]
experts.genetic_operators  <- experts/genetic_expert only                          [LEGACY]
experts.graph_expert  <- orchestrator, test/test_quality_metrics
experts.greedy_expert <- orchestrator, test/test_greedy_expert
experts.random_expert <- orchestrator, test/test_quality_metrics
exploration           <- exploration_shortlist.py (root CLI), visualization/html_generator, test/test_exploration
graph_builder         <- processing/__init__, experts/{graph,genetic}_expert, orchestrator, evolutionary_search_engine, analysis_sweep
group_mapper          <- processing/__init__, experts/{graph,genetic}_expert, test/test_metrics_revision
group_metrics         <- processing/__init__, experts/{baseline,genetic,greedy}_expert, group_mapper, random_group_builder, test/test_quality_metrics
harness               <- test/test_harness
job_filter            <- main.py, test/test_job_filter
orchestrator          <- processing/__init__, harness, tuner, analysis_sweep, scripts/{challenge_worker,phase1_measurement}, test/test_metrics_revision
policy                <- broad (all experts, orchestrator, group_mapper, evolutionary_*, tests)
quality_metrics       <- processing/__init__, config_dataclass, group_mapper, group_metrics,
                         random_group_builder, selection, valuation/overlap, evolutionary_fitness,
                         analysis_sweep, scripts/phase1_measurement, tests
random_group_builder  <- processing/__init__, experts/random_expert, test/{group_structure,objective_injection,pipeline_contracts}
selection             <- orchestrator, test/test_selection
stat_calculator       <- data/loaders, test/test_density
tuner                 <- main.py
valuation.density     <- break_log.py, stat_calculator, valuation/{economic,focus}, scripts/profile_snapshot, tests
valuation.economic    <- test/test_profit_objective
valuation.focus       <- experts/{baseline,greedy}_expert, exploration, group_metrics, valuation/economic,
                         analysis_sweep, scripts/challenge_coverage_gap, visualization/html_generator, tests
valuation.objective   <- broad (experts/*, orchestrator, random_group_builder, valuation/*, evolutionary_*, tests)
valuation.overlap     <- orchestrator, experts/greedy_expert, valuation/{__init__,economic}, scripts/challenge_coverage_gap, tests
valuation.prices      <- valuation/economic, test/{prices,profit_objective}
valuation.taux        <- exploration, valuation/economic, test/test_taux
```

Package-level imports (`from processing import ...`): `main.py`,
`test/test_pipeline_contracts.py`, `test/test_refactor_snapshot.py`,
`test/test_quality_metrics.py`.

## ZERO importers outside their own group

- `processing/experts/baseline_expert.py` — **ORPHAN**. `BaselineExpert` defined,
  never imported anywhere (not orchestrator, not any test). Phase 2 candidate.
- `processing/experts/__init__.py` — empty (0 bytes).

## Legacy reference map (Phase 1 targets)

| File | Referenced by |
|------|---------------|
| evolutionary_search_engine.py | processing/__init__, test/test_evolutionary_search |
| evolutionary_fitness.py | processing/__init__, evolutionary_search_engine |
| evolutionary_operators.py | processing/__init__, evolutionary_search_engine |
| evolutionary_search_state.py | evolutionary_{fitness,operators,search_engine}, test/test_evolutionary_search |
| experts/genetic_expert.py | test/test_warm_start |
| experts/genetic_operators.py | experts/genetic_expert only (dies with it) |

Classes: PortfolioEvolutionEngine, PortfolioFitnessEvaluator, PortfolioCandidate,
EvolutionaryArchive, WarmStartConfig, EvolutionaryOperators, GeneticGroupingExpert.

Config fields fed only by deleted code: `genetic_*` (5), `evolutionary_*` (12).
Tests to delete: test/test_evolutionary_search.py, test/test_warm_start.py.

NOTE: `PortfolioQualityEvaluator` / `PortfolioQualityWeights` / `portfolio_quality_weights`
are NOT legacy — they are the active portfolio scorer used by selection.py,
harness.py, tuner.py, config and analysis_sweep.py. Keep them.

## Phase 2 candidates (evidence)

| File | Importers | Verdict |
|------|-----------|---------|
| challenge_metrics.py | scripts/challenge_evaluate, test/test_challenge_metrics | USED but not by runtime pipeline -> propose move out of processing/ |
| selection.py | orchestrator (PortfolioSelector imported but never called; ProcessingReporter used), test/test_selection | PortfolioSelector = dead in runtime, test-only seam |
| stat_calculator.py | data/loaders, test/test_density | USED (loader) -> keep |
| exploration.py | exploration_shortlist.py, visualization/html_generator, test/test_exploration | USED -> keep |
| random_group_builder.py | processing/__init__, experts/random_expert, tests | USED -> keep |
| break_log.py | break_log.py, capture/break_ingestion, test/test_break_log | USED -> keep |
| experts/baseline_expert.py | NONE | ORPHAN -> delete (needs user OK) |
