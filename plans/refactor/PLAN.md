# PLAN — processing/ refactor (atomic steps)

Each step touches at most ONE module/concern and at most ~150 changed lines.
Verify with: `uv run pytest -q` + `python3 -m compileall -q processing`.
Commit after every green step. Two-strike rule applies.

---

## S01 — Delete dead code: stat_calculator.py
- **What**: Remove `validate_stat_weights`, `get_stat_weights_summary`, `calculate_equipment_weights_batch` (all 0 refs). Remove dead TODO block at bottom.
- **Files**: processing/stat_calculator.py
- **Verify**: pytest green; compileall clean
- **Risk**: low

## S02 — Delete dead code: equipment_filter.py
- **What**: Remove `get_pool_stats` (0 refs).
- **Files**: processing/equipment_filter.py
- **Verify**: pytest green
- **Risk**: low

## S03 — Delete dead code: group_mapper.py
- **What**: Remove `calculate_total_ingredients` (0 refs).
- **Files**: processing/group_mapper.py
- **Verify**: pytest green
- **Risk**: low

## S04 — Delete dead code: evolutionary_search_state.py
- **What**: Remove `diversity_sample`, `clear` (both 0 refs). Keep `best_candidate` (used by test/test_evolutionary_search.py).
- **Files**: processing/evolutionary_search_state.py
- **Verify**: pytest green
- **Risk**: low

## S05 — Extract GroupQualityEvaluator helper methods
- **What**: Extract `_compute_resource_usage` and `_compute_set_features` as module-level pure functions to shorten `evaluate()` below 40 lines.
- **Files**: processing/quality_metrics.py
- **Verify**: pytest green
- **Risk**: low

## S06 — Split evolutionary_search_engine.py by concern
- **What**: Extract `PortfolioFitnessEvaluator` to `processing/evolutionary_fitness.py`. Extract `EvolutionaryOperators` to `processing/evolutionary_operators.py`. Keep `PortfolioEvolutionEngine` in original file. Lazy import of `graph_builder` becomes top-level.
- **Files**: processing/evolutionary_search_engine.py → split into 3 files
- **Verify**: pytest green
- **Risk**: medium

## S07 — Split genetic_expert.py by concern
- **What**: Extract genetic operators (`_crossover`, `_resolve_conflicts`, `_mutate`, `_initialize_population`, `_create_graph_individual`) to `processing/experts/genetic_operators.py`. Keep `GeneticGroupingExpert` in original file.
- **Files**: processing/experts/genetic_expert.py → split into 2 files
- **Verify**: pytest green
- **Risk**: medium

## S08 — Extract shared inverted-index helper
- **What**: Introduce `processing/blocks/inverted_index.py` with a single `build_inverted_index(equipment_resources)` function. Switch `graph_builder._build_inverted_index` to use it (return set). Keep `random_group_builder._build_resource_index` as-is (needs list return type).
- **Files**: processing/blocks/inverted_index.py (new), processing/graph_builder.py
- **Verify**: pytest green
- **Risk**: low

## S09 — Deduplicate group_mapper map_communities / map_communities_inclusive
- **What**: Extract shared `_process_community` helper that handles split-then-filter logic. Both `map_communities` and `map_communities_inclusive` call it with different policy configs.
- **Files**: processing/group_mapper.py
- **Verify**: pytest green
- **Risk**: medium

## S10 — Extract shared expert-dispatch helper in orchestrator
- **What**: Extract `_build_shared_graph()` and `_dispatch_experts()` helpers used by `run_survey`, `run_committee`, and `run_evolutionary_committee`. Reduces duplication in graph building and expert error handling.
- **Files**: processing/orchestrator.py
- **Verify**: pytest green
- **Risk**: medium

## S11 — Remove print() from pure algorithms (edge reporting)
- **What**: Move `print()` calls from inside `GroupMapper.map_communities`, `CommunityDetector.find_best_louvain_partition`, and `EvolutionaryOperators` to the orchestrator/caller level (or remove where redundant with tqdm).
- **Files**: processing/group_mapper.py, processing/community_detector.py, processing/evolutionary_operators.py
- **Verify**: pytest green
- **Risk**: medium

## S12 — Consolidate config access in genetic_expert
- **What**: Pass `ProcessingConfig` values as parameters instead of reading `self.*` fields set from config in `discover_groups`. Reduces hidden state.
- **Files**: processing/experts/genetic_expert.py
- **Verify**: pytest green
- **Risk**: medium

## S13 — Tidy __init__.py exports
- **What**: Add `PortfolioEvolutionEngine`, `EvolutionaryOperators`, `PortfolioFitnessEvaluator` to `__init__.py` re-exports. Remove `EquipmentFilteringStrategy` if unused outside test (verify first).
- **Files**: processing/__init__.py
- **Verify**: pytest green
- **Risk**: low

## S14 — Tidy docstrings and type hints
- **What**: Shorten `config_dataclass.py` module docstring (move algorithm descriptions to PROCESSING.md if not already there). Add missing type hints to new files.
- **Files**: processing/config_dataclass.py, new files from S06/S07
- **Verify**: pytest green
- **Risk**: low

## S15 — Update PROCESSING.md file paths
- **What**: Update architecture section to reflect new file names from S06/S07/S08. Remove `resource_optimizer.py` reference (file doesn't exist).
- **Files**: processing/PROCESSING.md
- **Verify**: compileall clean (no code change)
- **Risk**: low

---

## Execution order rationale
1. S01–S04: Dead code first (verified 0 refs, zero risk)
2. S05–S07: Split oversized files (biggest win: 924→~300, 515→~200, 394→~250)
3. S08–S10: Deduplicate shared logic
4. S11–S12: I/O removal and config consolidation
5. S13–S15: Final tidy (exports, docstrings, docs)

## Line count targets (after all steps)
- evolutionary_search_engine.py: ~300 (down from 924)
- genetic_expert.py: ~200 (down from 515)
- orchestrator.py: ~250 (down from 423)
- group_mapper.py: ~250 (down from 394)
- quality_metrics.py: ~280 (down from 315)
- All others: unchanged or reduced
