# Constrain The Shopping List, Not The Item Count

## Objective

Bind the hard constraints to the thing that actually costs the player effort:
distinct line items and total units to carry.

## Depends On

[03-acceptance-policy.done.md](03-acceptance-policy.done.md),
[01-pure-blocks.done.md](01-pure-blocks.done.md)

## Scope

- Add `max_line_items` to `ProcessingConfig`, capping `unique_resource_count`.
- Add `max_total_units` capping `total_items_needed`, representing carry
  capacity.
- Apply both in `GroupAcceptancePolicy`.
- Relax `group_max_size`, or remove it as a primary constraint, so group size can
  grow while the list stays short.
- Both quantities are already computed and stored in the canonical group
  dictionary; this plan only constrains them.

## Acceptance Criteria

- A group of twenty items needing nine distinct resources is admissible. It is
  rejected today for exceeding `group_max_size`.
- A group of four items needing forty distinct resources is rejected. It is
  accepted today.
- Default values are chosen from the observed distribution rather than guessed,
  and the rationale is recorded in the config comment.

## Ownership

- Primary: `processing/policy.py`, `processing/config_dataclass.py`
- Docs: `processing/PROCESSING.md` configuration table

## Validation

- Construct both cases above as fixtures and assert the new admissibility.
- Report the distribution of `unique_resource_count` across current output before
  choosing defaults.

## Risks

Removing `group_max_size` entirely could allow very large groups that are
technically compact but impractical to craft in one session. Keep a generous
upper bound rather than none, and revisit once profit ranking exists, since the
profit objective penalises over-concentration through market impact.
