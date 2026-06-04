# Plan 08: Cache Pairwise Similarity in Community Detector

## Problem
`CommunityDetector.calculate_average_pairwise_similarity()` computes all-pairs Jaccard within each community for every resolution tried. With resolution range `(1, 10, 1)` trying 10 resolutions, the same pair's Jaccard is recomputed 10 times. For large communities (k > 50), this is expensive.

## Decision
Cache Jaccard results in a dictionary keyed by `(min_id, max_id)` tuple to avoid recomputing the same pair across different resolutions.

## Atomic Actions

### Action 8.1: Add `_jaccard_cache` parameter to `calculate_average_pairwise_similarity`
- **File:** `processing/community_detector.py`
- **Lines:** L18-75 (`calculate_average_pairwise_similarity` static method)
- **Change:** Add an optional cache parameter and use it to store/retrieve computed Jaccard values.
- **Details:**
  ```python
  @staticmethod
  def calculate_average_pairwise_similarity(
      partition: Dict[int, int],
      equipment_resources: Dict[int, Set[int]],
      _cache: Optional[Dict[Tuple[int, int], float]] = None,
  ) -> float:
  ```
  - Before computing Jaccard for a pair, check `_cache` keyed by `(min(eq1,eq2), max(eq1,eq2))`
  - After computing, store in `_cache` if provided
  - If `_cache` is `None`, behavior is unchanged (no caching)

### Action 82: Create and pass cache in `find_best_louvain_partition`
- **File:** `processing/community_detector.py`
- **Lines:** L122-168 (`find_best_louvain_partition` static method)
- **Change:** Create a cache dict before the resolution loop and pass it to each `calculate_average_pairwise_similarity` call.
- **Details:**
  ```python
  jaccard_cache: Dict[Tuple[int, int], float] = {}
  for resolution in np.arange(start, stop, step):
      partition = community.best_partition(...)
      pairwise_similarity = (
          CommunityDetector.calculate_average_pairwise_similarity(
              partition, equipment_resources, _cache=jaccard_cache
          )
      )
  ```

### Action 8.3: Add `Tuple` import if needed
- **File:** `processing/community_detector.py`
- **Lines:** L1-12 (imports)
- **Change:** Verify `Tuple` is imported from `typing`.
- **Details:** Add `Tuple` to the existing `typing` import if not present. Currently imports `Dict, List, Set` — need to add `Tuple`.
