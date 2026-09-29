# Unify The Value Gate Across All Methods

## Objective

Apply the item-value filter to every grouping method instead of only the random
expert, and make the threshold scale correctly with level.

## Depends On

[07-rune-density-relocation.md](07-rune-density-relocation.md)

## Scope

- Move density filtering out of `processing/equipment_filter.py`'s random-expert
  path and into the loader pool in `data/loaders.py`, where
  `min_equipment_density` already exists but defaults to zero.
- All five methods then inherit the same pool.
- Replace the linear `stat_weight >= level * ratio` rule with a within-level-band
  percentile. Stat budgets grow super-linearly with level, so the linear rule
  over-retains high-level items and over-rejects low-level ones.
- Remove the now-redundant random-expert filtering, including
  `fallback_to_unfiltered` and `min_filtered_pool_size` if they no longer apply.
- Update the configuration table in `PROCESSING.md`, which currently documents
  these fields as random-expert-only.

## Acceptance Criteria

- The equipment pool entering all five methods is identical.
- No emitted group contains an item below the configured percentile.
- `use_density_filtering` means what its name implies, rather than applying to
  one of five paths.
- The percentile is computed within level bands, and the band width is
  configurable.

## Ownership

- Primary: `data/loaders.py`, `processing/equipment_filter.py`
- Config: `processing/config_dataclass.py`
- Docs: `processing/PROCESSING.md`

## Validation

- Assert pool equality across methods.
- Compare retained-item level distributions under the linear rule and the
  percentile rule; the percentile should be roughly level-neutral.

## Risks

This shrinks the pool for four methods that previously saw everything, so group
counts will fall. That is the intended correction of Failing 6, but it is a
visible change. Record before/after pool sizes and group counts.

Note that until prices exist, `stat_weight` ranks by raw density rather than by
value, so the gate filters for "contains a lot of rune material" and not "is
worth breaking". Revisit the threshold after
[22-profit-objective.md](22-profit-objective.md).
