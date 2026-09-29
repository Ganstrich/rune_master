# Explainable Shortlist

## Objective

Make the existing report-time crafting ranking visible and understandable to a crafter.

## Scope

- Add a visible rank to each index card.
- Show the evidence used for ordering: sharing efficiency, shared-resource count, average density, and group size.
- Keep ranking logic unchanged and centralized in the report generator.
- Preserve group detail-page numbering and links after ranking.

## Acceptance Criteria

- The first card is visibly identified as the highest-ranked candidate.
- Every card exposes the ranking metrics without implying price or profit.
- Ties remain deterministic.
- Detail links point to the matching ranked group page.

## Ownership

- Primary: `visualization/html_generator.py`
- Tests: `test/test_pipeline_contracts.py`
- Styling, if needed: `visualization/static/index.css`

## Validation

- Add offline HTML assertions for rank and evidence labels.
- Run `uv run pytest -q`.
- Run the compile and `git diff --check` gates.
- Perform one browser check against a generated report separately.

## Risks

Sharing efficiency measures recipe reuse, not economic value. The UI must keep
that distinction explicit and avoid a fabricated composite score.
