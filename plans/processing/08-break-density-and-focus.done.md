# Break Density And Focus

## Objective

Implement the break-density formulas from the game guide, giving a per-item
measure of how much rune material an item contains. This requires no price data
and no coefficient.

## Depends On

[07-rune-density-relocation.done.md](07-rune-density-relocation.done.md)

## Scope

- Add `processing/valuation/focus.py`:

  ```python
  def break_density(item) -> float: ...                # sum(v_s * d_s)
  def break_density_focused(item, stat) -> float: ...  # v_f*d_f + 0.5*sum(rest)
  def best_focus(item, rho) -> str | None: ...         # needs prices; stub now
  ```

- Use the average of each stat line's minimum and maximum as $v_s$, matching the
  existing `calculate_stat_line_weight` convention, and clamp negative lines to
  zero.
- Expose `break_density` per item in group reports and in the canonical group
  dictionary.
- Leave `best_focus` present but returning `None` until prices exist; it is
  activated in [22-profit-objective.md](22-profit-objective.md).

## Acceptance Criteria

- `break_density_focused(item, f)` equals
  `v_f*d_f + 0.5 * sum(v_s*d_s for s != f)`, matching the published formula.
- For an item with a single stat line, focused and unfocused density are equal.
- Focusing never reduces total density below half the unfocused value.
- Items with no stats yield zero rather than raising.
- Grouping behavior is unchanged; this plan is additive.

## Ownership

- Primary: new `processing/valuation/focus.py`
- Reporting: `processing/group_metrics.py`, `visualization/html_generator.py`
- Docs: `processing/PROCESSING.md` group schema section

## Validation

- Unit tests against hand-computed examples for single-stat, two-stat, and
  negative-stat items.
- Confirm group membership and ordering are unchanged.

## Risks

The rune-count conversion is inferred, not verified: the guide gives the density
formula but not how density maps to rune quantity, and it states that yield also
depends on item level while the formula has no explicit level term
([../../docs/01-domain-model.md](../../docs/01-domain-model.md)). This plan
implements only the **verified** density formulas. Do not add a count conversion
here; that belongs in [32-taux-model.done.md](32-taux-model.done.md) where it can be
calibrated against observation.
