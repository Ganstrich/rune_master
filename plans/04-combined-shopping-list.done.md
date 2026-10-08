# Combined Shopping List

## Objective

Show the total ingredients needed across a user-selected set of equipment groups.

## Scope

- Allow selection of multiple generated groups in the static report.
- Aggregate resource quantities by resource ID.
- Preserve resource names, images, and per-group quantities where available.
- Keep each group's existing detail report unchanged.
- Support copying the combined resource list.

## Acceptance Criteria

- Aggregation uses resource IDs, not display names.
- Selecting and removing groups updates totals deterministically.
- Missing resource metadata remains visible as an explicit fallback.
- The result does not imply inventory ownership or market cost.

## Ownership

- Primary: `visualization/html_generator.py` and `visualization/static/utils.js`
- Canonical aggregation: `processing/group_metrics.py` where shared logic is needed
- Tests: offline aggregation and generated-report contracts

## Validation

- Test overlapping and disjoint resource sets offline.
- Test duplicate group selection behavior.
- Perform a browser check with at least three groups.
- Run the full working gate.

## Risks

A combined list can become large and may encourage users to treat recipe totals
as a shopping or inventory plan. Label it as a recipe requirement summary.
