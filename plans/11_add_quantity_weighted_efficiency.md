# Plan 11: Add Quantity-Weighted Efficiency Metric

## Problem
The sharing efficiency metric only considers **which** resources are shared, not **how many** of each. Two groups with the same efficiency score could have vastly different crafting costs — one might share 3 resources × 50 quantity each, another 3 resources × 5 quantity each. The metric treats them identically, undervaluing groups that share high-quantity resources.

## Decision
Add a new `weighted_sharing_efficiency` metric: `sum(shared_resource_quantities) / sum(all_resource_quantities)`. This better reflects actual crafting effort saved. Add it as a supplementary field in the group dict, computed alongside the existing `sharing_efficiency`.

## Atomic Actions

### Action 11.1: Add `calculate_weighted_efficiency` method to `GroupMapper`
- **File:** `processing/group_mapper.py`
- **Lines:** After L66 (after `calculate_shared_resources`)
- **Change:** Add a new method that computes quantity-weighted efficiency.
- **Details:**
  ```python
  def calculate_weighted_efficiency(
      self, group_equipments: List[Equipment]
  ) -> float:
      """Calculate quantity-weighted sharing efficiency.

      Weighted efficiency = sum(shared_resource_quantities) / sum(all_resource_quantities)
      where shared resources are those used by 2+ equipment (excluding excluded_ids).

      This better reflects actual crafting effort saved compared to
      the count-based sharing_efficiency.
      """
      resource_total_quantity: Dict[int, int] = {}
      resource_usage_count: Dict[int, int] = {}

      for equipment in group_equipments:
          for resource_id, qty in self._iter_equipment_recipe(equipment):
              resource_id = int(resource_id)
              resource_total_quantity[resource_id] = \
                  resource_total_quantity.get(resource_id, 0) + int(qty)
              resource_usage_count[resource_id] = \
                  resource_usage_count.get(resource_id, 0) + 1

      total_all = sum(resource_total_quantity.values())
      if total_all == 0:
          return 0.0

      shared_quantity = sum(
          qty for rid, qty in resource_total_quantity.items()
          if resource_usage_count[rid] > 1 and rid not in self.excluded_resource_ids
      )
      return shared_quantity / total_all
  ```

### Action 11.2: Include `weighted_sharing_efficiency` in `create_group` output
- **File:** `processing/group_mapper.py`
- **Lines:** L147-186 (`create_group` method)
- **Change:** Compute and include `weighted_sharing_efficiency` in the returned group dict.
- **Details:**
  - After computing `shared_count, total_shared, efficiency` (L164), add:
    ```python
    weighted_efficiency = self.calculate_weighted_efficiency(group_equipments)
    ```
  - Add `"weighted_sharing_efficiency": weighted_efficiency` to the returned dict

### Action 11.3: Add `weighted_sharing_efficiency` to `RandomGroupBuilder.build_random_group` output
- **File:** `processing/random_group_builder.py`
- **Lines:** L140-204 (`build_random_group` method)
- **Change:** Compute and include `weighted_sharing_efficiency` in the returned group dict.
- **Details:**
  - Add a `_calculate_weighted_efficiency` static method (similar to Action 11.1 but using `self.excluded_resource_ids`)
  - Compute it alongside `sharing_efficiency` at L186
  - Add `"weighted_sharing_efficiency": weighted_efficiency` to the returned dict at L189-204
