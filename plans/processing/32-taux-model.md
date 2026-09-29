# Taux Model

## Objective

Estimate the expected taux per item type from logged observations, accounting
for the fact that observations age and that breaking degrades the taux.

## Depends On

[30-break-log.done.md](30-break-log.done.md) with accumulated history

## Scope

- Add `processing/valuation/taux.py`:

  ```python
  class TauxModel(Protocol):
      def expected(self, item_id: int, planned_volume: int) -> float: ...
      def confidence(self, item_id: int) -> float: ...
      def exploration_bonus(self, item_id: int) -> float: ...
  ```

- `FlatTauxModel` stays as the no-data fallback.
- `PosteriorTauxModel` fits from `break_log`:
  - observed taux per row is `observed_density / theoretical_break_density`;
  - **age-weight observations** by an exponential decay with a configurable
    half-life, since an old observation describes a taux that has since moved;
  - decay `expected()` in `planned_volume`, because breaking an item type drives
    its own taux down.
- Add the exploration bonus: item types with few or no recent observations get a
  positive term, because discovering a high-taux item is the product.
- Wire into `ProfitObjective`, replacing the flat $\tau$.

## Acceptance Criteria

- An item with no observations returns the prior plus a full exploration bonus,
  never zero.
- Two identical items differing only in observation age produce different
  estimates, with the fresher one weighted more heavily.
- `expected()` is non-increasing in `planned_volume`.
- Confidence is reported alongside every estimate, and reports distinguish "high
  expected value" from "high uncertainty".

## Ownership

- Primary: new `processing/valuation/taux.py`
- Consumer: `processing/valuation/economic.py`

## Validation

- Backtest: fit on observations up to a cutoff, predict later observations,
  report error. This is the first genuine out-of-sample check the project has.
- Assert monotonic decay in both age and planned volume.

## Risks

Several quantities here are unresolved and must be treated as assumptions, not
facts ([../../docs/01-domain-model.md](../../docs/01-domain-model.md)):

- whether the taux attaches to the item **type** (server-wide) or the item
  **instance**, which changes the model substantially;
- whether the taux recovers over time when an item stops being broken;
- whether rune yield has an explicit level term beyond larger stat values.

Resolve the type-versus-instance question by observation before trusting any
fitted model. Until then, keep the half-life and decay parameters as explicit,
documented constants rather than fitted values.

## Out Of Scope

Learning a temporal model that *predicts* how the taux evolves, rather than
decaying stale observations by a fixed half-life, is deliberately excluded. The
half-life is a tunable constant for now. See the future-work note in
[../../docs/05-roadmap.md](../../docs/05-roadmap.md).
