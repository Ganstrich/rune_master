# Baseline And Evaluation Harness

## Objective

Provide a trivial baseline and a repeatable before/after comparison, so that
every later change can be shown to help rather than assumed to.

## Depends On

[02-objective-protocol.done.md](02-objective-protocol.done.md)

## Scope

- Add a `BaselineExpert`: take the top-K items by value density, then pack them
  greedily by `objective.marginal()`. No graph, no communities, no evolution.
- Add an evaluation harness that runs a named set of methods on a fixed seed and
  emits a comparison table: group count, group-size distribution, line-item
  distribution, mean group score, portfolio score, and runtime.
- Persist harness output so successive runs can be diffed.
- Register the baseline as a first-class method so it appears in the committee
  and in the tuner.

## Acceptance Criteria

- The harness runs offline against cached data with no network access.
- Output is deterministic for a fixed seed.
- Every existing expert is compared against the baseline on the same objective.
- The comparison is a single command.

## Ownership

- Primary: new `processing/experts/baseline_expert.py`, new harness entry point
- Tests: harness determinism test

## Validation

- Run the harness twice with the same seed and assert identical output.
- Publish the first comparison as the reference point for all later plans.

## Risks

The likely outcome is that the baseline is competitive with the graph and
genetic experts on the current objective. That is useful information, not a
failure: it would mean the search sophistication is not earning its complexity
under the present score, and that the objective rather than the search is what
needs work.

No expert has ever been compared to a baseline, and `quality_score` currently
grades its own output — it is simultaneously what the algorithms maximise, the
acceptance threshold, the ranking key, and the tuner's objective. Until Phase 3
provides observed break outcomes, this harness is the only external check
available.
