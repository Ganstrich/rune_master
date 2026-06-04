# Plan 04: Add Early Stopping to Genetic Algorithm

## Problem
The GA evolution loop always runs for the full `generations=50` iterations. A `stagnation_counter` is tracked (L85, L104) but **never used** to trigger early stopping. For large equipment pools where fitness converges quickly, this wastes significant computation.

## Decision
Add early stopping when `stagnation_counter` exceeds a configurable threshold (default: 15 generations without improvement). Also expose the threshold as a constructor parameter.

## Atomic Actions

### Action 4.1: Add `stagnation_limit` parameter to `GeneticGroupingExpert.__init__`
- **File:** `processing/experts/genetic_expert.py`
- **Lines:** L25-38 (`__init__` method)
- **Change:** Add `stagnation_limit: int = 15` parameter.
- **Details:**
  ```python
  def __init__(
      self,
      cache_manager: Optional[Any] = None,
      api_client: Optional[Any] = None,
      population_size: int = 30,
      generations: int = 50,
      mutation_rate: float = 0.3,
      elite_count: int = 3,
      stagnation_limit: int = 15,
  ):
      ...
      self.stagnation_limit = stagnation_limit
  ```

### Action 4.2: Add early stopping check in the evolution loop
- **File:** `processing/experts/genetic_expert.py`
- **Lines:** L87-134 (evolution loop, after stagnation_counter increment at L104)
- **Change:** After incrementing `stagnation_counter`, check if it exceeds the limit and break.
- **Details:** After line 104 (`stagnation_counter += 1`), add:
  ```python
  if stagnation_counter >= self.stagnation_limit:
      print(
          f"      [{self.name}] Early stopping at generation {gen + 1} "
          f"(stagnation: {stagnation_counter} generations)"
      )
      break
  ```

### Action 43: Print final generation info when early stopping triggers
- **File:** `processing/experts/genetic_expert.py`
- **Lines:** L129-134 (periodic print block)
- **Change:** No change needed — the existing print at `(gen + 1) % 10 == 0` will have printed the last milestone. The early stop message from Action 4.2 is sufficient.
