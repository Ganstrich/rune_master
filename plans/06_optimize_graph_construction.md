# Plan 06: Optimize Graph Construction from O(n²) to Inverted Index

## Problem
`GraphBuilder.create_jaccard_similarity_graph()` uses `itertools.combinations(equipment_nodes, 2)` to compare every pair of equipment — O(n²) Jaccard computations. For large equipment pools (thousands of items), this dominates runtime.

## Decision
Build an inverted index (`resource_id → [equipment_ids]`) first, then generate candidate pairs only from equipment that share at least one resource. This reduces comparisons to only pairs with non-zero Jaccard similarity.

## Atomic Actions

### Action 6.1: Add `_build_inverted_index` static method to `GraphBuilder`
- **File:** `processing/graph_builder.py`
- **Lines:** After L66 (after `get_equipment_resources`)
- **Change:** Add a new static method that builds a resource→equipment inverted index.
- **Details:**
  ```python
  @staticmethod
  def _build_inverted_index(
      equipment_resources: Dict[int, Set[int]]
  ) -> Dict[int, Set[int]]:
      """Build inverted index: resource_id -> set of equipment_ids."""
      index: Dict[int, Set[int]] = {}
      for eq_id, resources in equipment_resources.items():
          for rid in resources:
              index.setdefault(rid, set()).add(eq_id)
      return index
  ```

### Action 6.2: Add `_candidate_pairs_from_index` static method to `GraphBuilder`
- **File:** `processing/graph_builder.py`
- **Lines:** After `_build_inverted_index`
- **Change:** Add a method that generates candidate pairs from the inverted index.
- **Details:**
  ```python
  @staticmethod
  def _candidate_pairs_from_index(
      inverted_index: Dict[int, Set[int]]
  ) -> Set[Tuple[int, int]]:
      """Generate candidate equipment pairs that share at least one resource."""
      candidates: Set[Tuple[int, int]] = set()
      for equip_set in inverted_index.values():
          if len(equip_set) < 2:
              continue
          for eq1, eq2 in combinations(sorted(equip_set), 2):
              candidates.add((eq1, eq2))
      return candidates
  ```

### Action 6.3: Refactor `create_jaccard_similarity_graph` to use inverted index
- **File:** `processing/graph_builder.py`
- **Lines:** L68-109 (`create_jaccard_similarity_graph` method)
- **Change:** Replace the `combinations(equipment_nodes, 2)` loop with inverted-index-based candidate generation.
- **Details:**
  1. Call `_build_inverted_index(equipment_resources)` to build the index
  2. Call `_candidate_pairs_from_index(inverted_index)` to get candidate pairs
  3. Iterate over candidate pairs instead of all combinations
  4. Keep the existing Jaccard/absolute-count threshold logic unchanged
  5. Add isolated nodes (those with no candidates) back to the graph with `G.add_node()`

### Action 6.4: Add `Tuple` import if not present
- **File:** `processing/graph_builder.py`
- **Lines:** L1-10 (imports)
- **Change:** Verify `Tuple` is imported from `typing`. Currently `Dict, Set, List, Tuple` — `Tuple` is already present.
- **Details:** No change needed.
