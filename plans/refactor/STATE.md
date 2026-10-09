# STATE

Phase: C (complete)   Current step: PLAN.md written   Last green commit: fa07c7c

## Done
- Phase A: full inventory written to plans/refactor/INVENTORY.md.
- Phase B: baseline pytest (84 passed). Added test/test_refactor_snapshot.py
  with 8 characterization tests locking deterministic, random (seed=42),
  hybrid, density filtering (fallback on/off/none), get_summary keys/types,
  and run_all alias. All 8 pass on unmodified code.
- Full suite: 92 passed (84 original + 8 new). Committed as fa07c7c.
- Phase C: wrote plans/refactor/PLAN.md with 15 atomic steps (S01-S15).

## Next
- Await user approval of PLAN.md before executing Phase D.

## Notes (facts learned, so I do not re-read files)
- Snapshot values (deterministic, 10 items, algorithm=none):
  3 groups: [1,2,3,4] eff=0.333333 quality=0.570833; [5,6,7,8] same;
  [9,10] eff=0.333333 quality=0.420833. portfolio_quality_score=0.701542.
- Random seed=42: seeds=[2,1,7,4,5], groups=[1,2,3,4],[1,2,3,4],[5,6,7,8],[1,2,3,4],[5,6,7,8].
- Hybrid (det=3 + rand=3 supplement): 6 total.
- Density: strict+fallback→10 items unfiltered; strict+nofallback→0 items filtered; no_filter→10.
- 9 files over 250-line target. 8 dead-code symbols. 6 duplication groups.
- Dead code: validate_stat_weights, get_stat_weights_summary,
  calculate_equipment_weights_batch, get_pool_stats, calculate_total_ingredients,
  diversity_sample, EvolutionaryArchive.clear, EvolutionaryArchive.best_candidate.
- PROCESSING.md references resource_optimizer.py which does not exist (doc bug).
- graph_builder._build_inverted_index ≈ random_group_builder._build_resource_index.
- orchestrator run_survey/run_committee/run_evolutionary_committee share dispatch.
- group_mapper map_communities ≈ map_communities_inclusive.
- evolutionary_search_engine lazy-imports graph_builder at line 579.

## BLOCKED
- (none)
