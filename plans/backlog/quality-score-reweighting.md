---
status: backlog
last_reviewed: 2026-10-10
related: [plans/research/metrics-revision.md, plans/research/group-evaluation-spec.md]
---

# Plan: Quality Score Re-weighting Decision

## Objective

`metrics-revision.md` §1.1 recommends dropping `resource_reuse_ratio` from the
`quality_score` blend and keeping `compression` + `shared_quantity_ratio` +
`set_free_ratio` (reward) - `largest_set_share` (penalty). Re-weighting was explicitly
deferred. This plan proposes the re-weighting decision.

## Scope

- Propose new weights for the 4-term blend
- Justify weights against the three constraints (C1 large groups, C2 no set items, C3 shared resources)
- Define acceptance criteria for the new blend
- Plan A/B comparison against current weights on snapshot 3.7.7.6

## Acceptance Criteria

- New weights proposed with rationale tied to C1/C2/C3
- Old vs new blend compared on the same pool (coverage, group count, quality distribution)
- No metric gaming introduced (check against Goodhart risks in group-evaluation-spec.md §4)
- Decision recorded and committed

## Validation

- Run pipeline with old and new weights on identical config
- Compare coverage, group count, PQ, and per-band distribution
- Verify no single metric can be gamed to dominate the new blend
