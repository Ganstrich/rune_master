# Report Filtering and Sorting

## Objective

Help users narrow and reorder generated groups without rerunning the live pipeline.

## Scope

- Add client-side filtering and sorting to the static index.
- Support existing report fields only: rank, efficiency, density, group size, resource count, and grouping method where available.
- Keep the default order equal to the explainable shortlist order.
- Make the controls work without a server-side API.

## Acceptance Criteria

- Filtering updates visible cards without changing detail-page links.
- Sorting is deterministic and has a clear reset to default ranking.
- Empty results are communicated accessibly.
- The report remains usable on mobile and with keyboard navigation.

## Ownership

- Primary: `visualization/static/utils.js` and `visualization/html_generator.py`
- Styling: `visualization/static/index.css`
- Tests: generated HTML contract tests plus a focused JavaScript check if tooling permits

## Validation

- Run offline generation and HTML assertions.
- Perform browser checks for filtering, sorting, reset, empty state, and mobile layout.
- Run the full working gate.

## Risks

Client-side controls only affect the generated report and cannot recover groups
that were filtered out during processing.
