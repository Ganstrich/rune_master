# Plan 13: Implement Resource Optimizer

## Goal
Implement the resource optimizer that selects an optimal subset of groups to minimize total unique ingredients across all chosen groups.

## Current State
`processing/resource_optimizer.py` is empty (removed in Plan 05). The `ProcessingConfig.use_resource_optimizer` flag was removed. This feature was planned but never implemented.

## Problem Statement
Given N discovered groups, each requiring a set of ingredients, find the subset of groups that:
- Maximizes the number of equipment covered
- Minimizes the total unique ingredients needed (set cover variant)
- Respects practical constraints (max groups, min efficiency)

This is essentially a **weighted set cover problem** — NP-hard, but approximable with greedy heuristics.

## Approach
1. **Create a new `ResourceOptimizer` class** in `processing/resource_optimizer.py`:

```python
class ResourceOptimizer:
    """Selects an optimal subset of groups to minimize total unique ingredients."""
    
    def __init__(self, groups: List[Dict[str, Any]]):
        self.groups = groups
    
    def optimize(
        self,
        max_groups: int = 50,
        min_efficiency: float = 0.15,
    ) -> List[Dict[str, Any]]:
        """
        Greedy weighted set cover:
        1. Filter groups below min_efficiency
        2. Score each group by: (equipment_covered) / (unique_ingredients)
        3. Greedily pick the best group, remove covered equipment, repeat
        4. Stop when max_groups reached or all equipment covered
        """
```

2. **Add the optimizer to the orchestrator** — call it as a post-processing step in `RuneMaster`:
   ```python
   def _optimize_groups(self, groups):
       if len(groups) <= self.config.max_optimization_groups:
           return groups
       optimizer = ResourceOptimizer(groups)
       return optimizer.optimize(max_groups=self.config.max_optimization_groups)
   ```

3. **Add config parameters:**
   ```python
   max_optimization_groups: int = 50  # Max groups after optimization
   enable_group_optimization: bool = False  # Off by default
   ```

4. **Add optimization metadata** to the output:
   ```python
   "optimization_reduced_from": 200,  # Original group count
   "optimization_reduced_to": 45,     # After optimization
   ```

## Files Affected
- `processing/resource_optimizer.py` — new implementation
- `processing/config_dataclass.py` — add config fields
- `processing/orchestrator.py` — add optimization step

## Validation
- Create a test case with 20 groups where 5 groups cover 80% of equipment with minimal ingredients
- Verify the optimizer selects those 5 groups
- Run the full pipeline with `enable_group_optimization=True` and verify the output has fewer groups but similar equipment coverage
- Verify the total unique ingredients in the optimized set is less than the unoptimized set
