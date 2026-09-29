# Processing Plans

Atomic plans taking `processing/` from recipe-overlap grouping to profit-ranked,
coefficient-aware grouping. Background and rationale: [../../docs/](../../docs/README.md).

Each plan is one self-contained change with its own validation gate. Plans state
their dependencies; anything not listed as a dependency can proceed in parallel.

## Phasing

| Phase | Data required | Question it answers |
| --- | --- | --- |
| **1. Theory** (`01`-`12`) | None beyond the existing API | Which items share resources, and how much rune material do they contain? |
| **2. Prices** (`20`-`23`) | Captured rune/resource prices | Which groups are profitable at current market rates? |
| **3. Coefficient** (`30`-`32`) | Captured break outcomes | Which items actually carry a high taux? |

## Why Three Phases, Not Two

Prices give you $\rho$ (rune price per density) and craft cost, which is enough
to rank groups by *theoretical* profit. They do **not** give you $\tau$, the
1%-4000% break rate that dominates every other term
([../../docs/01-domain-model.md](../../docs/01-domain-model.md)). $\tau$ is
observable only by breaking items and recording the yield. Phase 3 closes that
loop, and it is the phase that produces the project's actual product.

Phase 3 depends on capture, but **not** on Phase 2 — break outcomes and market
prices are independent scrapes. If OCR of the market proves hard, Phase 3 can
proceed first.

## Sequencing Constraints

- `01`-`06` are behavior-preserving and unblock everything else.
- `20` (price table contract) is built during Phase 1 with a null source, so
  Phase 2 is a data change rather than a refactor.
- `30` (break log) should ship as early as possible regardless of when Phase 3
  starts. Its value scales with history length, so every week without it is
  permanently lost calibration data. It needs no capture — manual entry is
  enough.
- `12` (baseline harness) should land before any plan that changes output, so
  before/after comparisons are possible.

## Phase 1 — Theory

| Plan | Behavior change |
| --- | --- |
| [01-pure-blocks.done.md](01-pure-blocks.done.md) | No |
| [02-objective-protocol.done.md](02-objective-protocol.done.md) | No |
| [03-acceptance-policy.done.md](03-acceptance-policy.done.md) | No |
| [04-experts-consume-objective.md](04-experts-consume-objective.md) | No |
| [05-selection-module.md](05-selection-module.md) | No |
| [06-hygiene.done.md](06-hygiene.done.md) | No |
| [07-rune-density-relocation.done.md](07-rune-density-relocation.done.md) | No |
| [08-break-density-and-focus.done.md](08-break-density-and-focus.done.md) | Additive |
| [09-compression-term.done.md](09-compression-term.done.md) | **Yes** |
| [10-shopping-list-constraints.md](10-shopping-list-constraints.md) | **Yes** |
| [11-value-gate-unification.md](11-value-gate-unification.md) | **Yes** |
| [12-baseline-harness.done.md](12-baseline-harness.done.md) | No |

## Phase 2 — Prices

| Plan | Notes |
| --- | --- |
| [20-price-table-contract.done.md](20-price-table-contract.done.md) | Build during Phase 1, null source |
| [21-price-capture-ingestion.done.md](21-price-capture-ingestion.done.md) | Blocked on capture |
| [22-profit-objective.done.md](22-profit-objective.done.md) | Needs `20`, works with null prices |
| [23-evolve-under-profit.done.md](23-evolve-under-profit.done.md) | Warm-started evolution, not re-ranking |

## Phase 3 — Coefficient

| Plan | Notes |
| --- | --- |
| [30-break-log.done.md](30-break-log.done.md) | Ship early. Manual entry, no capture needed |
| [31-break-outcome-capture.done.md](31-break-outcome-capture.done.md) | Blocked on capture |
| [32-taux-model.md](32-taux-model.md) | Needs logged history |
| [33-exploration-shortlist.md](33-exploration-shortlist.md) | Useful from the first observation |

## The Manual Path

Phase 3 does **not** depend on capture. Observed break density can be entered by
hand into `break_log` with a timestamp ([30-break-log.done.md](30-break-log.done.md)), and
[33-exploration-shortlist.md](33-exploration-shortlist.md) turns that into a
ranked list of items worth testing next. Capture
([31-break-outcome-capture.done.md](31-break-outcome-capture.done.md)) later removes the
typing, not the capability.

This makes `30` and `33` the shortest route to something useful, and they can
run alongside Phase 1.

## Shared Validation Gate

Every plan must pass:

```bash
uv run pytest -q
python3 -m compileall -q data processing main.py config.py test visualization
git diff --check
```

Plans marked as changing behavior must additionally record group-size,
line-item-count, and portfolio-score distributions before and after, and state
which failing from
[../../docs/03-current-state-audit.md](../../docs/03-current-state-audit.md)
they address.

Any plan that changes runtime behavior must update
[../../processing/PROCESSING.md](../../processing/PROCESSING.md) in the same
change.
