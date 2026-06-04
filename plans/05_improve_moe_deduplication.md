# Plan 05: Improve MoE De-duplication with Overlap Threshold

## Problem
The MoE de-duplication in `run_committee()` uses exact set equality (`equip_ids not in seen_equipment_sets`). This means:
1. Identical groups from different experts are deduplicated (correct)
2. **Overlapping but non-identical groups are kept even if they share 90% of equipment**, causing the same equipment to appear in many groups

This reduces the practical value of the ensemble — users want diverse groups covering different equipment, not 5 near-duplicate groups.

## Decision
Add a configurable overlap threshold (Jaccard similarity of equipment sets). When a candidate group's equipment set has Jaccard similarity > threshold with any already-accepted group, keep the one with higher fitness and discard the other.

## Atomic Actions

### Action 5.1: Add `dedup_overlap_threshold` config parameter
- **File:** `processing/config_dataclass.py`
- **Lines:** L45-46 (end of dataclass fields)
- **Change:** Add a new field for the de-duplication overlap threshold.
- **Details:**
  ```python
  # MoE De-duplication
  dedup_overlap_threshold: float = 0.7  # Jaccard similarity threshold for considering groups as duplicates
  ```

### Action 5.2: Add Jaccard similarity helper method to `RuneMaster`
- **File:** `processing/orchestrator.py`
- **Lines:** After L50 (after `__init__`, before `run_all`)
- **Change:** Add a static helper method for computing Jaccard similarity between two equipment groups.
- **Details:**
  ```python
  @staticmethod
  def _equipment_set_overlap(group_a: List[Equipment], group_b: List[Equipment]) -> float:
      """Compute Jaccard similarity between two groups' equipment sets."""
      ids_a = {e.ankama_id for e in group_a}
      ids_b = {e.ankama_id for e in group_b}
      intersection = len(ids_a & ids_b)
      union = len(ids_a | ids_b)
      return intersection / union if union > 0 else 0.0
  ```

### Action 5.3: Replace exact-match de-duplication with overlap-threshold de-duplication
- **File:** `processing/orchestrator.py`
- **Lines:** L128-140 (de-duplication loop in `run_committee`)
- **Change:** Replace the exact `equip_ids not in seen_equipment_sets` check with overlap-based comparison.
- **Details:**
  ```python
  # Overlap-based de-duplication
  is_duplicate = False
  for existing_group in unique_groups:
      overlap = self._equipment_set_overlap(
          group["equipments"], existing_group["equipments"]
      )
      if overlap >= self.config.dedup_overlap_threshold:
          is_duplicate = True
          break

  if not is_duplicate:
      unique_groups.append(group)
  ```
  - Remove the `seen_equipment_sets` list (no longer needed)
  - Since groups are already sorted by fitness (descending), the first-seen group always has higher fitness — we always keep the existing one and skip the new duplicate

### Action 5.4: Update print message to reflect overlap-based deduplication
- **File:** `processing/orchestrator.py`
- **Lines:** L144-145 (print statements after de-duplication)
- **Change:** No change needed — the existing messages are still accurate.
