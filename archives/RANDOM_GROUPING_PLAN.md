# Implementation Plan: Density/Level Ratio Filtering + Random Selection Feature

## Purpose
Transform RuneMaster from a deterministic "find all communities" approach to a **random-selection-based grouping engine** that:
1. Filters equipment pool by density/level ratio before processing
2. Allows toggling between filtered and fallback pools
3. Randomly selects a seed equipment, then finds companions sharing resources
4. Provides both exploration (random) and optimization (filtered communities) modes

---

## Phase 1: Add Density/Level Ratio Filtering

### 1.1 Extend ProcessingConfig (`processing/orchestrator.py`)
- Add new config options:
  - `equipment_density_level_ratio: float` (e.g., 0.15 = 15% of level)
  - `use_density_filtering: bool` (toggle on/off)
  - `fallback_to_unfiltered: bool` (try unfiltered if filtered pool too small)
  - `min_filtered_pool_size: int` (threshold before fallback)

**Why**: Centralize filtering strategy in configuration for easy tuning

### 1.2 Create FilteredEquipmentPool class (`processing/equipment_filter.py` - NEW)
```python
class EquipmentFilteringStrategy:
    - calculate_minimum_density(level, ratio) -> float
    - filter_by_density_ratio(equipments, ratio) -> List[Equipment]
    - get_active_pool(equipments, config) -> List[Equipment]
      (returns filtered pool, or falls back to all if too small)
    
Purpose: Encapsulate filtering logic, separate from orchestrator
```

**Why**: Keep filtering logic testable and reusable; follows separation of concerns

---

## Phase 2: Implement Random Selection + Resource Matching

### 2.1 Create RandomGroupBuilder class (`processing/random_group_builder.py` - NEW)
```python
class RandomGroupBuilder:
    def __init__(equipments, excluded_resource_ids, seed=None)
    
    def select_random_seed(equipment_pool) -> Equipment
        - Randomly pick one equipment from pool
        - Purpose: Starting point for companion search
    
    def find_companions(seed_equipment, equipment_pool, 
                       min_shared_resources=2) -> List[Equipment]
        - Extract resources from seed
        - Filter pool for items sharing ≥ min_shared_resources
        - Return sorted by % resources shared (descending)
    
    def build_random_group(equipment_pool, 
                          min_shared_resources=2,
                          max_group_size=18) -> Dict[str, Any]
        - Select seed
        - Find companions
        - Return group dict (same format as GroupMapper output)
        - Format: {
            'equipments': [seed, companion1, companion2, ...],
            'shared_resources_count': int,
            'sharing_efficiency': float,
            'total_ingredients': {...},
            'selection_method': 'random',
            'seed_equipment_id': int,
            'randomness_seed': int (for reproducibility)
          }
    
    def build_multiple_random_groups(equipment_pool, count=10,
                                    **kwargs) -> List[Dict]
        - Generate N random groups
        - Avoid duplicate seeds (track used)
        - Return list of group dicts

Purpose: Implement the random selection + companion-finding algorithm
```

**Why**: 
- Separates random logic from deterministic community detection
- Allows reproducible randomness (via seed parameter)
- Reusable for different filtering strategies

---

## Phase 3: Integrate into RuneMaster Orchestrator

### 3.1 Extend RuneMaster class (`processing/orchestrator.py`)
Add new methods:
```python
class RuneMaster:
    def run_random_grouping(self) -> List[Dict[str, Any]]
        - Step 1: Get active pool (filtered or fallback)
        - Step 2: Apply EquipmentFilteringStrategy
        - Step 3: Call RandomGroupBuilder.build_multiple_random_groups()
        - Step 4: Return results
        
    def run_hybrid_grouping(self) -> List[Dict[str, Any]]
        - Step 1: Try filtered pool approach
        - Step 2: If too few groups, supplement with random from unfiltered
        - Step 3: Deduplicate across both methods
        - Step 4: Return combined results
        
    def get_grouping_method(self) -> str
        - Return: "deterministic" | "random" | "hybrid"
        - Based on config settings
```

### 3.2 Update main.py (`main.py`)
```python
def process_equipment(...):
    - NEW: Accept grouping_method parameter
    - If "random": call master.run_random_grouping()
    - If "hybrid": call master.run_hybrid_grouping()
    - Else: call master.run_all() (existing deterministic)
    
    - NEW: Add CLI flag: --grouping-method [deterministic|random|hybrid]
```

**Why**: Allow user to choose grouping strategy without code changes

---

## Phase 4: Configuration & User Interface

### 4.1 Extend ProcessingConfig (`processing/orchestrator.py`)
```python
@dataclass
class ProcessingConfig:
    # ... existing fields ...
    
    # NEW: Filtering & Random Selection
    use_density_filtering: bool = True
    equipment_density_level_ratio: float = 0.15  # e.g., 15% of item level
    grouping_method: str = "deterministic"  # "random" | "hybrid" | "deterministic"
    random_group_count: int = 10  # How many random groups to generate
    fallback_to_unfiltered: bool = True
    min_filtered_pool_size: int = 10  # Min items before fallback
    random_seed: Optional[int] = None  # For reproducibility
```

### 4.2 Update config.py (`config.py`)
```python
class Config:
    # ... existing ...
    
    # NEW: Density/Level Filtering
    DENSITY_LEVEL_RATIO = 0.15  # Equipment must have stat_weight >= 15% of level
    FALLBACK_TO_UNFILTERED = True
    MIN_FILTERED_POOL_SIZE = 10
    GROUPING_METHOD = "deterministic"  # or "random", "hybrid"
    RANDOM_GROUP_COUNT = 10
```

**Why**: Centralize configuration for easy tuning and environment-specific overrides

---

## Phase 5: Visualization & Reporting Changes

### 5.1 Update HTMLGenerator (`visualization/html_generator.py`)
- Add `selection_method` field display on group pages
  - Show "🎯 Deterministic Community Detection" vs "🎲 Random Selection"
  - Display seed equipment if `selection_method == 'random'`
  
- NEW: Add filtering info to index page
  - "Pool size: 150 → 45 (filtered by density/level ratio)"
  - Toggle button to show both filtered & unfiltered results

### 5.2 Create group metadata footer (`visualization/html_generator.py`)
- Show for random groups:
  - Seed equipment name
  - Number of companions found
  - Randomness seed (for reproducibility)

**Why**: Users understand how each group was created

---

## Phase 6: Error Handling & Validation

### 6.1 Add validation (`processing/equipment_filter.py` + `processing/random_group_builder.py`)
```
Checks:
- Filtered pool not empty (else fallback)
- Min shared resources achievable (warn if no companions found)
- Random seed stability (log for reproducibility)
- Edge cases: single equipment, no resources, etc.
```

### 6.2 Add logging (both modules)
```
Log:
- Pool filtering: "Filtered from 250 → 45 equipment"
- Random selection: "Selected seed: Adamantine Sword (#1001)"
- Companion finding: "Found 3 companions sharing 4+ resources"
- Fallback: "Filtered pool too small, using unfiltered for companion search"
```

**Why**: Debugging and user transparency

---

## Phase 7: Testing Strategy

### 7.1 Unit tests (test suite)
```
Test EquipmentFilteringStrategy:
- calculate_minimum_density()
- filter_by_density_ratio()
- Fallback logic

Test RandomGroupBuilder:
- select_random_seed() returns valid Equipment
- find_companions() returns shared-resource matches
- Reproducibility with same seed
- Edge cases (empty pool, single item, no matches)

Test RuneMaster:
- run_random_grouping() produces correct format
- run_hybrid_grouping() merges correctly
```

### 7.2 Integration tests
```
Test end-to-end:
- main.py --grouping-method random
- main.py --grouping-method hybrid
- Filtering applied correctly
- Visualization generates without errors
```

**Why**: Ensure reliability before production use

---

## Implementation Order (Recommended)

1. **Phase 1**: Add config options + filtering strategy class
2. **Phase 2**: Build RandomGroupBuilder class
3. **Phase 3**: Integrate into RuneMaster with new methods
4. **Phase 4**: Update config files
5. **Phase 5**: Add UI/visualization features
6. **Phase 6**: Error handling + logging
7. **Phase 7**: Testing

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Separate classes for filtering & random** | Keeps code modular and testable |
| **Configuration-driven toggles** | Users can switch strategies without code changes |
| **Fallback mechanism** | Gracefully handles edge cases (small pools) |
| **Reproducible randomness** | Support via random_seed parameter |
| **Same output format** | Visualization code works for all methods |
| **Metadata tracking** | Show selection method in UI |

---

## File Structure Summary

```
NEW FILES:
  processing/equipment_filter.py       (filtering logic)
  processing/random_group_builder.py   (random selection)

MODIFIED FILES:
  processing/orchestrator.py           (add run_random_grouping, config)
  main.py                              (add --grouping-method flag)
  config.py                            (add new config options)
  visualization/html_generator.py      (show selection metadata)

TESTING:
  test/test_equipment_filter.py        (NEW)
  test/test_random_group_builder.py    (NEW)
  test/test_orchestrator_random.py     (NEW)
```

---

## Benefits of This Approach

✅ **Modular**: Filtering, random selection, and visualization are separate concerns  
✅ **Flexible**: Easy to toggle between deterministic, random, and hybrid modes  
✅ **Reproducible**: Random seed support for consistent results  
✅ **Resilient**: Fallback mechanism handles edge cases  
✅ **Observable**: Logging and metadata show exactly what happened  
✅ **Backward Compatible**: Existing deterministic mode unchanged  
✅ **User-Friendly**: Config-driven, no code changes needed  
