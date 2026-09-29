# Extract Portfolio Selection

## Objective

Separate portfolio assembly from method dispatch so `RuneMaster` only routes,
and the way a final set of groups is chosen becomes a testable component.

## Depends On

[02-objective-protocol.done.md](02-objective-protocol.done.md)

## Scope

- Add `processing/selection.py` owning the greedy proposal scan, the
  equipment-overlap dedup, and portfolio scoring.
- Move `run_committee`'s selection loop and `_equipment_set_overlap` out of
  `orchestrator.py`.
- Move `get_summary`, `print_summary`, and `get_expert_report` into a reporting
  helper; `orchestrator.py` retains dispatch only.
- Rename the committee path, or document plainly that it is a union with dedup
  rather than a mixture of experts. There is no gating and no expert weighting,
  and all experts are ranked by an identical score.
- No change to selection behavior in this plan.

## Acceptance Criteria

- `orchestrator.py` contains dispatch and nothing else.
- Selection is testable without constructing experts.
- Summary output is byte-identical.
- Expert failure recording still works and is still surfaced.

## Ownership

- Primary: new `processing/selection.py`, `processing/orchestrator.py`
- Tests: existing pipeline contract tests, plus direct unit tests for selection

## Validation

- Feed a fixed list of proposal dictionaries to selection and assert the chosen
  set matches the current implementation.
- Confirm the full pipeline output is unchanged on a fixed seed.

## Risks

`run_committee` catches five exception types from experts and continues. Preserve
that behavior exactly when moving the loop; silently narrowing it would turn a
degraded run into a crash.
