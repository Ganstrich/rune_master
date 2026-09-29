# Profit Objective

## Objective

Implement a `GroupObjective` denominated in kamas, so groups are ranked by
expected profit rather than by recipe overlap.

## Depends On

[20-price-table-contract.done.md](20-price-table-contract.done.md),
[08-break-density-and-focus.done.md](08-break-density-and-focus.done.md)

## Scope

- Add `processing/valuation/economic.py` implementing `ProfitObjective`:

  $$\text{Value}(G) = \sum_{i} n_i\bigl[\tau_i \cdot D_i(f_i) \cdot \rho_{f_i} - c_i\bigr] - \lambda\bigl|\bigcup_i R_i\bigr|$$

- $\rho_f$ is rune price divided by rune density; $c_i$ is craft cost at spot.
- Add `FlatTauxModel` returning a constant $\tau$, so this ships before any break
  data exists.
- Activate `best_focus(item, rho)` from
  [08-break-density-and-focus.done.md](08-break-density-and-focus.done.md). Focus is a
  decision variable: the chosen focus must be recorded on the group.
- Add $\lambda$ to config as the kama-equivalent fixed cost of acquiring one
  distinct resource, with a documented default.
- Fall back to `OverlapObjective` when prices are missing, rather than treating
  missing prices as zero.
- Defer the market-impact term; record it as future work.

## Acceptance Criteria

- With `NullPriceSource`, behavior is identical to `OverlapObjective`.
- With prices, groups are ranked by kamas and the unit of the score is stated in
  reports.
- Every valued item records which focus was assumed.
- A group whose revenue does not cover its craft cost scores negative and is
  visibly unprofitable rather than merely low-ranked.
- Partial price coverage degrades gracefully: items with unknown prices are
  excluded from the profit term and counted separately, not valued at zero.

## Ownership

- Primary: new `processing/valuation/economic.py`
- Config: $\lambda$, flat $\tau$, staleness tolerance
- Docs: `processing/PROCESSING.md`, `docs/02-objective-model.md`

## Validation

- Assert equivalence to `OverlapObjective` under null prices.
- Hand-compute profit for a two-item fixture and assert the objective matches.
- Confirm the guide's focus rule emerges: focusing should win when the target
  rune's price-per-density is roughly twice the density-weighted average of the
  other lines.

## Risks

$\tau$ is held constant here, and it is the dominant term with a 1% to 4000%
range. Ranking by profit with a flat $\tau$ ranks by *theoretical* profit and
will be confidently wrong about which items are actually worth breaking. Label
the output accordingly until [32-taux-model.md](32-taux-model.md) lands.

The fallback to overlap must be explicit in reports. A user cannot distinguish a
kama-denominated ranking from an overlap ranking by looking at group membership
alone.
