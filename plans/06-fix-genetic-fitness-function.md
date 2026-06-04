# Plan 06: Fix Genetic Expert Fitness Function

## Goal
Fix the inverted fitness function in the genetic expert so it correctly rewards high resource-sharing groups.

## Current State
In `processing/experts/genetic_expert.py:L140-174`, the `_calculate_individual_fitness` method computes:

```python
efficiency = len(unique_resources) / len(all_resources)
sharing_score = (1.0 - efficiency) * len(eq_set)
```

This is **backwards**: when `efficiency` is high (many shared resources relative to total), `(1.0 - efficiency)` becomes *low*, penalizing good groups.

## Problems
- Groups with high resource sharing get low fitness scores
- The genetic algorithm evolves toward groups that share *fewer* resources — the opposite of what a craft optimizer needs
- This makes the genetic expert produce worse results than random selection

## Fix

Replace the inverted formula with one that rewards high sharing:

```python
# efficiency = unique_resources / total_resource_instances
# High efficiency = many duplicates = good sharing
# Reward: high efficiency * large group size
sharing_score = efficiency * len(eq_set)
```

Additionally:
- Rename `efficiency` to `resource_deduplication_ratio` for clarity (it's not the same as `GroupMapper`'s `sharing_efficiency`)
- Add a minimum group size check: groups smaller than `config.group_min_size` should get a fitness of 0
- Consider adding a bonus for groups where the shared resources are a high proportion of each member's recipe (not just the group aggregate)

## Files Affected
- `processing/experts/genetic_expert.py` — `_calculate_individual_fitness` method (L140-174)

## Validation
- Create a test case: two groups, one with high sharing and one with low sharing. Verify the high-sharing group gets a higher fitness score.
- Run the genetic expert standalone and verify the output groups have higher average `sharing_efficiency` than before the fix
- Run `python main.py --grouping-method genetic --no-serve` — confirm it produces reasonable groups
