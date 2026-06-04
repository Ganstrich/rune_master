# Plan 14: Add "Craftability" Score

## Goal
Create a single composite "craftability" score that combines efficiency, level range, ingredient rarity, and pod weight into one group quality metric.

## Current State
Groups are evaluated by multiple independent metrics:
- `sharing_efficiency` — ratio of shared to total unique resources
- `average_density` — mean stat weight of equipment in the group
- `shared_resources_count` — absolute count of shared resources
- `unique_ingredients_count` — total unique ingredients

No single score combines these into a "how useful is this group for crafting?" metric.

## Problems
- The tuner's `evaluate_quality` function uses `average_efficiency` with arbitrary weights (30/40/30)
- Users can't easily compare groups across different metrics
- The genetic expert's fitness function is ad-hoc and doesn't align with what makes a group actually craftable

## Approach
Define a `craftability_score` for each group:

```
craftability = (
    w1 * sharing_efficiency +          # How much resource overlap
    w2 * level_cohesion +              # How close levels are (1.0 = same level)
    w3 * ingredient_rarity_score +     # How rare/valuable the shared ingredients are
    w4 * size_score +                  # Sweet spot for group size (2-8)
    w5 * profession_bonus              # Bonus for single-profession groups
)
```

Where:
- `level_cohesion = 1.0 - (max_level - min_level) / max_level_spread` (clamped to 0-1)
- `ingredient_rarity_score` = average level of shared resources / max resource level in dataset
- `size_score` = 1.0 for groups of 2-8, linearly decreasing to 0 at 18
- `profession_bonus` = 0.1 if single profession, 0.0 if mixed

Default weights: `w1=0.35, w2=0.20, w3=0.15, w4=0.20, w5=0.10`

### Implementation
1. **Add a `calculate_craftability(group)` static method** to `GroupMapper`
2. **Add the score to the group dict** in `create_group()`
3. **Update the tuner** to use `average_craftability` instead of the ad-hoc quality function
4. **Update the genetic expert** to use craftability as its fitness function
5. **Make weights configurable** via `ProcessingConfig`

## Files Affected
- `processing/group_mapper.py` — add `calculate_craftability`, update `create_group`
- `processing/config_dataclass.py` — add craftability weight fields
- `processing/tuner.py` — update `evaluate_quality`
- `processing/experts/genetic_expert.py` — use craftability in fitness

## Validation
- Manually inspect the top 10 groups by craftability — they should be genuinely useful for crafting
- Compare the ranking by craftability vs ranking by sharing_efficiency — they should differ meaningfully
- Run the tuner and verify it selects configs that maximize average craftability
