# Single Acceptance Policy

## Objective

Move all admissibility constraints into one component so a group is accepted or
rejected by exactly one rule set, applied once.

## Depends On

[01-pure-blocks.md](01-pure-blocks.md)

## Scope

- Add `processing/policy.py` with a `GroupAcceptancePolicy` built from
  `ProcessingConfig`, exposing `accepts(group) -> bool` and a reason for
  rejection.
- Move the size, shared-resource, efficiency, and quality gates into it.
- Replace the three current application sites: `group_mapper.py`,
  `genetic_expert.py` (inside `_calculate_individual_fitness`), and
  `random_expert.py`.
- Fix the divergent filter in `genetic_expert.py`, which compares
  `resource_reuse_ratio` against `group_efficiency_threshold` while
  `group_mapper.py` compares `sharing_efficiency` against the same value.
  Standardise on the `group_mapper` semantics for this plan; changing the
  threshold's meaning is out of scope here.
- Keep policy separate from objective. Policy answers "is this admissible",
  objective answers "is this good".

## Acceptance Criteria

- Exactly one module applies acceptance thresholds.
- The graph path and the genetic path accept an identical set of candidate
  groups for the same config. This test fails today.
- Rejection reasons are available for reporting and debugging.
- No group is filtered twice.

## Ownership

- Primary: new `processing/policy.py`
- Callers updated: `group_mapper.py`, `experts/genetic_expert.py`,
  `experts/random_expert.py`
- Tests: cross-expert acceptance parity test

## Validation

- Generate candidate groups, run them through both the graph and genetic
  acceptance paths, and assert the accepted sets are equal.
- Confirm group counts are unchanged on a fixed seed, except where the genetic
  path previously diverged; document any difference.

## Risks

Standardising the genetic expert's filter will change its output, since it
currently uses a different formula. This is a correctness fix, but it is a
behavior change in an otherwise behavior-preserving plan. Record before/after
group counts and call it out explicitly in the change description.
