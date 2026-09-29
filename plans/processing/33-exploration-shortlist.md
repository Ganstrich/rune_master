# Exploration Shortlist

## Objective

Produce a ranked list of items worth *trying* — items whose taux is unknown or
stale but whose theoretical value and craft cost make them cheap to test.

## Depends On

[30-break-log.md](30-break-log.md). Works with manual observations only; does
not require capture or prices.

## Scope

- Add a report ranking candidate items by exploration value:
  - high theoretical `break_density` relative to craft cost;
  - few or no observations, or observations older than the configured
    half-life;
  - already present in a proposed group, so testing them costs nothing extra.
- Surface the shortlist in the HTML report and as a CLI listing.
- Show, per item: theoretical break density, observation count, age of the most
  recent observation, and last observed taux if any.
- Provide a direct path from the shortlist to recording an observation, closing
  the loop.

## Acceptance Criteria

- Never-broken items appear, and are visibly distinguished from items with a
  known poor taux.
- Items whose last observation has aged past the half-life reappear as worth
  retesting.
- The shortlist works with zero observations, ranking purely on theoretical
  density and cost.
- With prices absent, ranking falls back to density per resource unit rather
  than silently failing.

## Ownership

- Primary: new reporting path, `visualization/html_generator.py`
- Data: `break_log`, `processing/valuation/focus.py`

## Validation

- With an empty log, the shortlist ranks by theoretical density and is
  non-empty.
- After recording a poor observation, the item drops; after the half-life
  elapses, it rises again.

## Risks

This is the most directly useful output of the whole system before capture
exists: it tells the player what to test next, and each test feeds `break_log`.
It should therefore be built early, not held until Phase 3 completes.

The shortlist encourages breaking items, which drives their taux down. That is
intended — the information is the point — but the report should say plainly that
a good result will decay with use, so a discovered item is exploited promptly
rather than saved.
