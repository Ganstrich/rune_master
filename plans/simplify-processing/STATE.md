# STATE — simplify processing/

Branch: `refactor/simplify-processing`   Last green commit: a5490c5 (start)

## Done
- Phase 0 baseline captured (plans/simplify-processing/PHASE0.md).
  Tests 156 passed. CLI 18 groups, deterministic across runs.

## Next
- Phase 1: delete legacy evolutionary + genetic files, fix refs, commit.

## Notes (facts learned, avoid re-reading)
- Compare tool: /tmp/baseline/compare_vis.py A B  (group pages + group-data + cards).
- Baseline CLI cmd:
  uv run main.py --no-serve --grouping-method greedy --random-seed 0 --min-level 1 --max-level 40 --item-types ring,amulet
- PortfolioQualityEvaluator is ACTIVE (selection/harness/tuner/analysis_sweep). NOT legacy.
- baseline_expert.py is orphaned (0 importers).
- plans/refactor/*.md is a PRIOR completed refactor; do not overwrite, it is stale.
- To compare two output dirs, regenerate with `rm -rf visualizations` first.

## BLOCKED
- (none)
