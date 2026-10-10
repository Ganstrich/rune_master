---
status: backlog
last_reviewed: 2026-10-10
related: [plans/research/pipeline-challenge.md]
---

# Plan: Update Pipeline Challenge for Active Method Set

## Objective

`plans/research/pipeline-challenge.md` was written for 8 methods. Four were removed in
commit `82a32ba` (genetic, evolutionary_committee, committee, baseline). Update the plan
to reflect the current 5-method set and 3-expert set.

## Scope

- Update §3.1 (8 methods -> 5 methods) with note about removed methods
- Update §3.2 (5 experts -> 3 experts) with note about removed experts
- Update C2 (genetic/evo graph-bound -> deterministic graph-bound)
- Update C9 (evo vs committee -> hybrid vs deterministic)
- Update runtime guard reference (committee -> removed methods)

## Acceptance Criteria

- All method counts match the codebase (5 methods, 3 experts)
- No references to removed methods without "removed in 82a32ba" annotation
- All referenced experts exist in `processing/experts/`

## Validation

- `grep -rn "genetic\|evolutionary_committee\|committee\|baseline" plans/research/pipeline-challenge.md` returns only annotated removal notes
- Cross-check method list against `main.py` --grouping-method choices
