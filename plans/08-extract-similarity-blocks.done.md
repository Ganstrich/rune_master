# Phase 0.1: Extract Similarity Blocks

## Objective

Create a single module for all similarity functions, eliminating the four
existing Jaccard implementations with divergent signatures.

## Scope

- Create `processing/blocks/similarity.py` as the single source for Jaccard
  and future similarity functions (IDF-weighted, cosine).
- Replace the four existing implementations:
  - `processing/quality_metrics.py` (two copies: one in `evaluate()`, one in
    `PortfolioQualityEvaluator.evaluate()`)
  - `processing/orchestrator.py` (inline in `PortfolioSelector.select()`)
  - `processing/graph_builder.py` (imported from `blocks/similarity`)
  - `processing/community_detector.py` (inline in
    `calculate_average_pairwise_similarity()`)
- Normalize the function signature: `jaccard(left: Collection, right: Collection) -> float`.
- Keep `processing/blocks/recipes.py` as-is for now (it already exists).

## Acceptance Criteria

- `jaccard()` is importable from `processing.blocks.similarity`.
- All existing tests pass unchanged.
- A grep for `def jaccard` returns exactly one result (in `blocks/similarity.py`).
- Results are numerically identical to the current implementations.

## Ownership

- Primary: `processing/blocks/similarity.py` (new)
- Modify: `processing/quality_metrics.py`, `processing/orchestrator.py`,
  `processing/graph_builder.py`, `processing/community_detector.py`

## Validation

- Run `uv run pytest -q` — all tests pass.
- Run `python3 -m compileall -q processing` — no errors.
- Run `grep -rn "def jaccard" processing/` — exactly one match.

## Risks

- The four implementations may have subtle differences in edge-case handling
  (empty sets, identical sets). Verify each produces identical results before
  replacing.
