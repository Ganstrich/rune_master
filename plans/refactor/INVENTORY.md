# INVENTORY — processing/ package

## Files (path, lines, responsibility, public API, importers, smells)

### processing/__init__.py (39)
- Responsibility: Public API re-exports
- Public: ProcessingConfig, RuneMaster, GraphBuilder, CommunityDetector, GroupMapper, GroupMetrics, EquipmentFilteringStrategy, RandomGroupBuilder, GroupQualityEvaluator, GroupQualityMetrics, GroupQualityWeights, PortfolioQualityEvaluator, PortfolioQualityMetrics, PortfolioQualityWeights
- Importers: main.py (ProcessingConfig, RuneMaster), test/test_pipeline_contracts.py, test/test_quality_metrics.py
- Smells: None

### processing/config_dataclass.py (153)
- Responsibility: ProcessingConfig dataclass with all config fields and defaults
- Public: ProcessingConfig
- Importers: orchestrator, experts/*, graph_builder, group_mapper, policy, selection, tuner, evolutionary_search_engine, random_group_builder, harness, test/*
- Smells: Large docstring (lines 1-63) mixes config docs with algorithm descriptions

### processing/orchestrator.py (423)
- Responsibility: RuneMaster orchestrator — method dispatch, hybrid/committee/evolutionary pipelines, summary
- Public: RuneMaster
- Importers: main.py, tuner.py, harness.py, test/*
- Smells: >300 lines; print() calls inside methods (I/O); run_survey and run_committee share graph-building and expert-dispatch duplication; run_evolutionary_committee is >100 lines

### processing/group_mapper.py (394)
- Responsibility: Maps communities to canonical equipment groups with filtering/splitting
- Public: GroupMapper
- Importers: experts/graph_expert, experts/genetic_expert, test/*
- Smells: >300 lines; map_communities and map_communities_inclusive share significant duplication; print() and tqdm inside; calculate_total_ingredients is dead code (0 refs)

### processing/group_metrics.py (163)
- Responsibility: Canonical group dict builder, shared resources, density, ingredient aggregation
- Public: GroupMetrics
- Importers: group_mapper, experts/genetic_expert, experts/baseline_expert, experts/greedy_expert, random_group_builder, test/*
- Smells: None major

### processing/quality_metrics.py (315)
- Responsibility: GroupQualityEvaluator (item-only features) and PortfolioQualityEvaluator (portfolio-level)
- Public: GroupQualityEvaluator, GroupQualityMetrics, GroupQualityWeights, PortfolioQualityEvaluator, PortfolioQualityMetrics, PortfolioQualityWeights
- Importers: config_dataclass, group_metrics, group_mapper, selection, evolutionary_search_engine, valuation/overlap, test/*
- Smells: >300 lines; evaluate() method is ~50 lines (borderline)

### processing/graph_builder.py (251)
- Responsibility: Bipartite graph + Jaccard similarity graph construction
- Public: GraphBuilder
- Importers: orchestrator, experts/graph_expert, experts/genetic_expert, evolutionary_search_engine, test/*
- Smells: None major

### processing/community_detector.py (228)
- Responsibility: Louvain/BiLouvain community detection with resolution search
- Public: CommunityDetector
- Importers: experts/graph_expert, test/*
- Smells: None major

### processing/evolutionary_search_engine.py (924)
- Responsibility: PortfolioEvolutionEngine, EvolutionaryOperators, PortfolioFitnessEvaluator
- Public: PortfolioEvolutionEngine
- Importers: orchestrator, test/test_evolutionary_search.py
- Smells: WAY over target (924 vs 250); extensive print() calls; PortfolioFitnessEvaluator.evaluate() is ~50 lines; evolve_portfolio is ~100 lines; EvolutionaryOperators has 6 methods each ~20-30 lines

### processing/evolutionary_search_state.py (160)
- Responsibility: PortfolioCandidate, EvolutionaryArchive, WarmStartConfig
- Public: PortfolioCandidate, EvolutionaryArchive, WarmStartConfig
- Importers: evolutionary_search_engine, orchestrator, test/test_evolutionary_search.py
- Smells: diversity_sample (dead, 0 refs), best_candidate (test-only), clear (dead, 0 refs)

### processing/experts/base.py (53)
- Responsibility: GroupingExpert ABC with discover_groups interface
- Public: GroupingExpert
- Importers: all experts
- Smells: None

### processing/experts/graph_expert.py (127)
- Responsibility: Deterministic graph/community detection grouping
- Public: GraphGroupingExpert
- Importers: orchestrator
- Smells: None

### processing/experts/random_expert.py (63)
- Responsibility: Random grouping with density filtering
- Public: RandomGroupingExpert
- Importers: orchestrator
- Smells: None

### processing/experts/genetic_expert.py (515)
- Responsibility: Genetic algorithm grouping expert
- Public: GeneticGroupingExpert
- Importers: orchestrator, test/test_warm_start.py
- Smells: Over target (515 vs 250); discover_groups is ~50 lines; _initialize_population, _create_graph_individual, _calculate_individual_fitness, _crossover, _resolve_conflicts, _mutate all 30-50 lines; print() calls

### processing/experts/baseline_expert.py (122)
- Responsibility: Baseline greedy break-density packing
- Public: BaselineExpert
- Importers: orchestrator, harness
- Smells: None

### processing/experts/greedy_expert.py (169)
- Responsibility: Greedy objective-driven grouping
- Public: GreedyGroupingExpert
- Importers: orchestrator
- Smells: None

### processing/random_group_builder.py (260)
- Responsibility: Random seed-and-companion group builder
- Public: RandomGroupBuilder
- Importers: experts/random_expert, test/*
- Smells: At target boundary; find_companions is ~50 lines; select_random_seed is internal-only

### processing/equipment_filter.py (154)
- Responsibility: Equipment density/level ratio filtering
- Public: EquipmentFilteringStrategy
- Importers: __init__.py, test/*
- Smells: get_pool_stats is dead code (0 refs)

### processing/policy.py (63)
- Responsibility: GroupAcceptancePolicy — single acceptance policy for all thresholds
- Public: GroupAcceptancePolicy
- Importers: orchestrator, experts/*, group_mapper, evolutionary_search_engine, selection, test/*
- Smells: None

### processing/selection.py (96)
- Responsibility: PortfolioSelector (greedy dedup) and ProcessingReporter (summary)
- Public: PortfolioSelector, ProcessingReporter
- Importers: orchestrator, test/test_selection.py
- Smells: None

### processing/tuner.py (142)
- Responsibility: ParameterTuner — parallel grid search for config
- Public: ParameterTuner
- Importers: main.py
- Smells: _worker_run_config is ~30 lines (ok)

### processing/stat_calculator.py (221)
- Responsibility: Stat weight calculation (used by data/loaders.py upstream)
- Public: calculate_stat_line_weight, calculate_equipment_weight, STAT_WEIGHTS, validate_stat_weights, get_stat_weights_summary, calculate_equipment_weights_batch
- Importers: data/loaders.py (calculate_equipment_weight), test/test_density.py (STAT_WEIGHTS)
- Smells: validate_stat_weights (dead, 0 refs), get_stat_weights_summary (dead, 0 refs), calculate_equipment_weights_batch (dead, 0 refs)

### processing/exploration.py (77)
- Responsibility: ExplorationCandidate ranking for break-rate testing
- Public: rank_exploration, ExplorationCandidate
- Importers: visualization/html_generator.py, exploration_shortlist.py
- Smells: None

### processing/harness.py (58)
- Responsibility: Offline comparison harness
- Public: run_comparison, write_comparison
- Importers: test/test_harness.py
- Smells: None

### processing/break_log.py (15)
- Responsibility: Break-log helpers for observed taux
- Public: observed_taux, rune_density
- Importers: test/test_break_log.py
- Smells: None

### processing/blocks/__init__.py (14)
- Responsibility: Re-exports pure helpers
- Public: ShoppingList, iter_recipe, jaccard, merge, recipe_resource_ids, resource_totals
- Importers: (re-exported)
- Smells: None

### processing/blocks/similarity.py (11)
- Responsibility: Jaccard similarity
- Public: jaccard
- Importers: graph_builder, community_detector, quality_metrics, selection, test/*
- Smells: None

### processing/blocks/recipes.py (40)
- Responsibility: Recipe normalization helpers
- Public: iter_recipe, recipe_resource_ids
- Importers: group_metrics, group_mapper, experts/baseline_expert, experts/greedy_expert, exploration, blocks/shopping_list, valuation/economic
- Smells: None

### processing/blocks/shopping_list.py (83)
- Responsibility: ShoppingList dataclass for resource aggregation
- Public: ShoppingList, merge, resource_totals
- Importers: __init__.py, test/test_processing_blocks.py
- Smells: None

### processing/valuation/__init__.py (6)
- Responsibility: Re-exports GroupCandidate, GroupObjective, OverlapObjective
- Importers: (re-exported)
- Smells: None

### processing/valuation/overlap.py (18)
- Responsibility: OverlapObjective — current price-independent objective
- Public: OverlapObjective
- Importers: orchestrator, experts/greedy_expert, valuation/economic, test/*
- Smells: None

### processing/valuation/objective.py (40)
- Responsibility: GroupCandidate value object, GroupObjective protocol
- Public: GroupCandidate, GroupObjective
- Importers: experts/*, evolutionary_search_engine, valuation/overlap, test/*
- Smells: None

### processing/valuation/prices.py (48)
- Responsibility: PriceSource protocol, NullPriceSource, CachePriceSource
- Public: PriceSource, NullPriceSource, CachePriceSource
- Importers: valuation/economic, test/test_prices.py
- Smells: None

### processing/valuation/focus.py (51)
- Responsibility: break_density, break_density_focused, best_focus
- Public: break_density, break_density_focused, best_focus
- Importers: group_metrics, experts/baseline_expert, experts/greedy_expert, exploration, valuation/economic, visualization
- Smells: None

### processing/valuation/density.py (60)
- Responsibility: RUNE_DENSITY table, resolve_stat_name
- Public: RUNE_DENSITY, resolve_stat_name
- Importers: stat_calculator, valuation/focus, test/test_density.py, test/test_break_log.py
- Smells: None

### processing/valuation/taux.py (64)
- Responsibility: PosteriorTauxModel with age-weighted observations
- Public: PosteriorTauxModel, TauxModel
- Importers: exploration, valuation/economic, test/test_taux.py
- Smells: None

### processing/valuation/economic.py (125)
- Responsibility: ProfitObjective, FlatTauxModel
- Public: ProfitObjective, FlatTauxModel
- Importers: test/test_profit_objective.py
- Smells: None

## Import graph (A -> B, inside processing/)

```
__init__.py -> config_dataclass, orchestrator, graph_builder, community_detector, group_mapper, group_metrics, equipment_filter, random_group_builder, quality_metrics
orchestrator -> config_dataclass, experts/genetic_expert, experts/graph_expert, experts/random_expert, experts/baseline_expert, experts/greedy_expert, graph_builder, policy, selection, valuation/objective, valuation/overlap, evolutionary_search_state, evolutionary_search_engine
experts/base -> config_dataclass, valuation/objective
experts/graph_expert -> community_detector, config_dataclass, experts/base, graph_builder, group_mapper, policy, valuation/objective
experts/random_expert -> experts/base, config_dataclass, random_group_builder, policy, valuation/objective
experts/genetic_expert -> experts/base, config_dataclass, graph_builder, group_mapper, group_metrics, policy, valuation/objective
experts/baseline_expert -> blocks/recipes, config_dataclass, experts/base, group_metrics, policy, valuation/focus, valuation/objective
experts/greedy_expert -> blocks/recipes, config_dataclass, experts/base, group_metrics, policy, valuation/objective, valuation/overlap, valuation/focus
graph_builder -> blocks/similarity
group_mapper -> blocks/recipes, group_metrics, policy, quality_metrics
group_metrics -> blocks/recipes, quality_metrics, valuation/focus
quality_metrics -> blocks/similarity
community_detector -> blocks/similarity
random_group_builder -> blocks/recipes, group_metrics, quality_metrics, valuation/objective
evolutionary_search_engine -> config_dataclass, evolutionary_search_state, policy, quality_metrics, valuation/objective, graph_builder (lazy import)
evolutionary_search_state -> (none)
selection -> blocks/similarity, quality_metrics
tuner -> config_dataclass, orchestrator
stat_calculator -> valuation/density
exploration -> blocks/recipes, valuation/focus, valuation/taux
valuation/economic -> blocks/recipes, valuation/focus, valuation/objective, valuation/overlap, valuation/prices, valuation/taux
valuation/overlap -> quality_metrics, valuation/objective
```

## Dead code candidates (verified 0 refs repo-wide, excluding def line)

| Symbol | File | Notes |
|---|---|---|
| validate_stat_weights | stat_calculator.py | 0 refs |
| get_stat_weights_summary | stat_calculator.py | 0 refs |
| calculate_equipment_weights_batch | stat_calculator.py | 0 refs |
| get_pool_stats | equipment_filter.py | 0 refs |
| calculate_total_ingredients | group_mapper.py | 0 refs |
| diversity_sample | evolutionary_search_state.py | 0 refs |
| EvolutionaryArchive.clear | evolutionary_search_state.py | 0 refs |
| EvolutionaryArchive.best_candidate | evolutionary_search_state.py | Only in test/test_evolutionary_search.py |

Note: PROCESSING.md references `resource_optimizer.py` (line 552) but that file does not exist. Doc bug, not code bug.

## Duplicated logic groups

1. **group_mapper.map_communities <-> map_communities_inclusive**: Significant structural duplication — both iterate communities, resolve equipment, split large groups, create groups, apply policy. Different thresholds and stats tracking.

2. **orchestrator.run_survey <-> run_committee**: Both build shared graph, dispatch to all experts with same error handling, collect proposals. run_survey merges by fingerprint; run_committee scores and selects.

3. **orchestrator.run_committee <-> run_evolutionary_committee**: Both build shared graph and dispatch to experts. Evolutionary adds warm-start and engine.

4. **random_group_builder._build_resource_index <-> graph_builder._build_inverted_index**: Both build resource_id -> set(equipment_ids) inverted indexes. Different return types (list vs set) and different filtering.

5. **quality_metrics.GroupQualityEvaluator <-> group_metrics.GroupMetrics**: Both compute shared resource counts. Different definitions (exclusion handling differs).

6. **evolutionary_search_engine.PortfolioFitnessEvaluator.evaluate <-> quality_metrics.PortfolioQualityEvaluator.evaluate**: PortfolioFitnessEvaluator wraps PortfolioQualityEvaluator but adds group-level objective scoring and policy checking.

## __init__.py re-exports

ProcessingConfig, RuneMaster, GraphBuilder, CommunityDetector, GroupMapper, GroupMetrics, EquipmentFilteringStrategy, RandomGroupBuilder, GroupQualityEvaluator, GroupQualityMetrics, GroupQualityWeights, PortfolioQualityEvaluator, PortfolioQualityMetrics, PortfolioQualityWeights
