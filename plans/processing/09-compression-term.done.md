# Compression Term In The Overlap Objective

## Objective

Stop the objective from decaying with group size, so the system proposes the
large, varied groups the project needs rather than converging on item pairs.

## Depends On

[02-objective-protocol.done.md](02-objective-protocol.done.md),
[12-baseline-harness.md](12-baseline-harness.md)

## Scope

- Add a compression feature to `OverlapObjective`:

  $$\text{compression} = 1 - \frac{|\bigcup_i R_i|}{\sum_i |R_i|}$$

  Zero for disjoint recipes, approaching $1 - 1/n$ for identical ones, and
  increasing in group size.
- **Remove `mean_pairwise_jaccard` and `overlapping_pair_ratio` from scoring.**
  They are the main drivers of the size bias. Keep computing both and keep them
  in `GroupQualityMetrics` as reported diagnostics; only their weights are
  removed.
- New `GroupQualityWeights`:

  | Feature | Weight |
  | --- | ---: |
  | `compression` | 0.50 |
  | `resource_reuse_ratio` | 0.30 |
  | `shared_quantity_ratio` | 0.20 |

  The 0.50 replacing the two removed features preserves the relative weight of
  the two retained ones.
- Report items-per-line-item (`group_size / unique_resource_count`) as a
  human-facing number alongside the score.
- Update `PROCESSING.md` and the `quality_metrics` feature table.

## Decision

**Resolved: replace.** Compression supersedes `mean_pairwise_jaccard` and
`overlapping_pair_ratio` rather than sitting alongside them.

This is the sharper break from current output, and it is the correct one. Both
removed features average over $\binom{n}{2}$ pairs, so each added item
contributes $n$ new and typically weaker pairs, pulling the mean down. No
reweighting fixes that; the features are structurally wrong for the goal.

## Implementation Notes

- `GroupQualityWeights.normalized()` builds its weight map with `asdict(self)`,
  so the weights dataclass fields must correspond exactly to the keys of the
  `features` dict in `GroupQualityEvaluator.evaluate()`. Removing two weight
  fields therefore requires removing the same two keys from `features`, while
  the metrics dataclass retains them.
- This changes the positional signature of `GroupQualityWeights`. Any caller
  constructing it positionally as `(0.30, 0.30, 0.20, 0.20)` will silently
  misassign. Search for construction sites, including the tuner's worker config.

## Acceptance Criteria

- Adding an item whose recipe is a subset of the group's existing resource union
  never lowers the score. This is the monotonicity property the current score
  lacks. All three retained features are individually non-decreasing under such
  an addition, so the property holds for any non-negative weights — assert it
  regardless, since it guards future reweighting.
- A ten-item group sharing eight of twelve resources scores above a two-item
  group with identical recipes.
- Group-size distribution shifts upward measurably against the baseline.
- `group_max_size` becomes a binding constraint rather than a formality.
- `mean_pairwise_jaccard` and `overlapping_pair_ratio` remain present in group
  reports and in `quality_metrics`, with no effect on ranking.

## Ownership

- Primary: `processing/valuation/overlap.py`,
  `processing/quality_metrics.py`
- Docs: `processing/PROCESSING.md`

## Validation

- Monotonicity property test as above.
- Record group-size and line-item distributions before and after.
- Confirm the pathological case from the audit: two identical-recipe items must
  no longer achieve the maximum score.

## Risks

This changes every downstream number, including the tuner's objective and any
stored report. Land it after [12-baseline-harness.md](12-baseline-harness.md) so
the shift is measured rather than assumed. Expect existing contract tests that
assert specific scores to need updating; update them with a stated reason rather
than loosening assertions.
