# STATE — simplify processing/

Branch: `refactor/simplify-processing`   Last green commit: 154f2db

## Done
- Phase 0 baseline (plans/simplify-processing/PHASE0.md). Tests 156 passed.
- Phase 1 delete legacy (commit ed32a85). Tests 156 -> 135.
- Phase 2 dead/orphan removal + challenge_metrics -> analysis/ (d888512). 135 -> 134.
- Phase 3 restructure into graph/filters/metrics/tools (33f31a8). Root 23 -> 4.
- Phase 4 tidy + docs (80ec37a, 154f2db).

## Final numbers
- Root files: 23 -> 4 (__init__, orchestrator, config, policy).
- Tests: 156 -> 134 passed (removed 22 legacy-only tests, added 0).
- CLI greedy smoke: 18 groups, byte-identical to baseline at every phase.

## Notes (facts learned, avoid re-reading)
- Compare tool: /tmp/baseline/compare_vis.py A B  (group pages + group-data + cards).
- Baseline CLI cmd:
  uv run main.py --no-serve --grouping-method greedy --random-seed 0 --min-level 1 --max-level 40 --item-types ring,amulet
- PortfolioQualityEvaluator is ACTIVE (selection/harness/tuner/analysis_sweep). NOT legacy.
- baseline_expert deleted (orphan); GroupingExpert ABC kept in experts/base.py.
- dead symbols from the old inventory (validate_stat_weights, get_pool_stats,
  calculate_total_ingredients) were already removed by a prior refactor.
- plans/refactor/*.md is a PRIOR completed refactor; do not overwrite, it is stale.

## BLOCKED
- (none)
