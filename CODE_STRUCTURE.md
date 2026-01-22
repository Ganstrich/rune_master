# Random Grouping Feature - Code Structure

## New Files

### `processing/equipment_filter.py` (155 lines)

```python
class EquipmentFilteringStrategy:
    @staticmethod
    def calculate_minimum_density(level, ratio) -> float
        # Returns: level * ratio
        
    @staticmethod
    def filter_by_density_ratio(equipments, ratio) -> tuple
        # Returns: (filtered_equipments, excluded_equipments)
        # Filters: stat_weight >= level * ratio
        
    @staticmethod
    def get_active_pool(equipments, use_filtering, density_ratio, 
                       fallback_to_unfiltered, min_pool_size) -> tuple
        # Returns: (active_pool, was_filtered)
        # Implements fallback logic if pool too small
        
    @staticmethod
    def get_pool_stats(equipments) -> dict
        # Returns: Pool statistics (avg/min/max density, etc.)
```

**Usage:**
```python
from processing.equipment_filter import EquipmentFilteringStrategy

# Filter equipment
filtered, excluded = EquipmentFilteringStrategy.filter_by_density_ratio(
    equipments, ratio=0.15
)

# Get active pool with fallback
pool, was_filtered = EquipmentFilteringStrategy.get_active_pool(
    equipments, 
    use_filtering=True,
    density_ratio=0.15,
    fallback_to_unfiltered=True,
    min_pool_size=10
)

# Get stats for parameter tuning
stats = EquipmentFilteringStrategy.get_pool_stats(equipments)
print(f"Avg density: {stats['avg_density']}")
```

---

### `processing/random_group_builder.py` (300 lines)

```python
class RandomGroupBuilder:
    def __init__(equipments, excluded_resource_ids, seed=None)
        # Stores pool and RNG seed
        
    def select_random_seed(equipment_pool, used_seeds=None) -> Equipment
        # Returns: Random Equipment or None
        # Avoids seeds in used_seeds set
        
    def find_companions(seed_equipment, equipment_pool, 
                       min_shared_resources=2, exclude_seed=True) -> List[Equipment]
        # Returns: List of Equipment sharing resources with seed
        # Sorted by sharing efficiency (high to low)
        
    def build_random_group(equipment_pool, seed_equipment=None,
                          min_shared_resources=2, max_group_size=18) -> Dict
        # Returns: Group dict with format:
        # {
        #     "equipments": [seed, companion1, ...],
        #     "shared_resources_count": int,
        #     "sharing_efficiency": float,
        #     "total_ingredients": {...},
        #     "selection_method": "random",
        #     "seed_equipment_id": int,
        #     "randomness_seed": int
        # }
        
    def build_multiple_random_groups(equipment_pool, count=10,
                                    min_shared_resources=2, max_group_size=18,
                                    avoid_seed_duplicates=True) -> List[Dict]
        # Returns: List of count group dicts
        # Avoids reusing same seed if avoid_seed_duplicates=True
        
    @staticmethod
    def _calculate_shared_resources(equipments) -> set
        # Helper: Returns resources in ALL equipments
        
    @staticmethod
    def _aggregate_resources(equipments) -> Dict[int, int]
        # Helper: Returns {resource_id: total_quantity}
        
    @staticmethod
    def _calculate_efficiency(equipments) -> float
        # Helper: Returns unique_resources / total_requirements
```

**Usage:**
```python
from processing.random_group_builder import RandomGroupBuilder

# Create builder (reproducible randomness)
builder = RandomGroupBuilder(
    equipments=all_equipments,
    excluded_resource_ids={15263, 14635},
    seed=42  # Optional: for reproducibility
)

# Build single random group
group = builder.build_random_group(
    equipment_pool=filtered_equipments,
    min_shared_resources=2,
    max_group_size=18
)

# Build multiple random groups
groups = builder.build_multiple_random_groups(
    equipment_pool=filtered_equipments,
    count=10,
    min_shared_resources=2,
    max_group_size=18,
    avoid_seed_duplicates=True
)
```

---

## Modified Files

### `processing/orchestrator.py` (439 lines)

**ProcessingConfig (dataclass):**
```python
@dataclass
class ProcessingConfig:
    # Existing fields...
    
    # NEW: Density filtering
    use_density_filtering: bool = True
    equipment_density_level_ratio: float = 0.15
    fallback_to_unfiltered: bool = True
    min_filtered_pool_size: int = 10
    
    # NEW: Random/Hybrid grouping
    grouping_method: str = "deterministic"
    random_group_count: int = 10
    random_seed: Optional[int] = None
```

**RuneMaster (class):**
```python
class RuneMaster:
    # Existing methods:
    def run_all() -> List[Dict[str, Any]]
    def build_graph() -> tuple
    def detect_communities() -> Dict[int, int]
    def map_groups() -> List[Dict[str, Any]]
    def optimize_groups() -> List[Dict[str, Any]]
    
    # NEW methods:
    def run_random_grouping() -> List[Dict[str, Any]]
        # Uses EquipmentFilteringStrategy + RandomGroupBuilder
        # Steps:
        #   1. Apply density filtering
        #   2. Generate random groups
        #   3. Return results
        
    def run_hybrid_grouping() -> List[Dict[str, Any]]
        # Combines deterministic + random
        # Steps:
        #   1. Run deterministic (run_all)
        #   2. If results < threshold, add random groups
        #   3. Merge and return
        
    def get_grouping_method() -> str
        # Returns: "deterministic", "random", or "hybrid"
```

**New imports:**
```python
from processing.equipment_filter import EquipmentFilteringStrategy
from processing.random_group_builder import RandomGroupBuilder
```

---

### `config.py` (38 lines)

**New Config constants:**
```python
class Config:
    # Existing...
    
    # NEW: Density filtering
    DENSITY_LEVEL_RATIO = 0.15
    FALLBACK_TO_UNFILTERED = True
    MIN_FILTERED_POOL_SIZE = 10
    
    # NEW: Grouping method
    GROUPING_METHOD = "deterministic"
    RANDOM_GROUP_COUNT = 10
```

---

### `main.py` (367 lines)

**New imports:**
```python
import argparse
```

**Updated process_equipment():**
```python
def process_equipment(
    equipments: List[Equipment],
    cache_manager=None,
    api_client=None,
    grouping_method: str = None,           # NEW
    random_group_count: int = None,        # NEW
    density_level_ratio: float = None,     # NEW
) -> List[dict]:
    # NEW: Use parameters or Config defaults
    # NEW: Call appropriate RuneMaster method
```

**Updated main():**
```python
def main():
    # NEW: Parse CLI arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--grouping-method", 
                       choices=["deterministic", "random", "hybrid"])
    parser.add_argument("--random-groups", type=int)
    parser.add_argument("--density-ratio", type=float)
    args = parser.parse_args()
    
    # ... pass to process_equipment(grouping_method=args.grouping_method, ...)
```

**CLI arguments:**
```
--grouping-method {deterministic,random,hybrid}
  Choose grouping method

--random-groups COUNT
  Number of random groups to generate

--density-ratio RATIO
  Density/level ratio filter (e.g., 0.15)
```

---

### `processing/__init__.py` (39 lines)

**New exports:**
```python
from processing.equipment_filter import EquipmentFilteringStrategy
from processing.random_group_builder import RandomGroupBuilder

__all__ = [
    # ... existing ...
    "EquipmentFilteringStrategy",
    "RandomGroupBuilder",
]
```

---

## Processing Flow Diagrams

### Random Grouping Pipeline
```
Equipment List
    ↓
EquipmentFilteringStrategy
    ├─ Filter by density/level ratio
    └─ Fallback if pool too small
    ↓
Active Pool (filtered or unfiltered)
    ↓
RandomGroupBuilder
    ├─ Select random seed
    ├─ Find companions (by shared resources)
    ├─ Repeat count times
    └─ Avoid seed duplicates
    ↓
List of Random Groups
    ↓
Visualization & Output
```

### Hybrid Grouping Pipeline
```
Equipment List
    ├─────→ Deterministic Path
    │       ├─ Build graph
    │       ├─ Detect communities
    │       └─ Map to groups
    │       ↓
    │   Deterministic Groups
    │
    └─────→ Random Path (if needed)
            ├─ Filter by density
            ├─ Generate random groups
            └─ Return random groups
            ↓
        Random Groups

Combine deterministic + random
    ↓
Final Groups List
    ↓
Visualization & Output
```

---

## Data Flow: Group Creation

### Random Group Object
```
Group = {
    "equipments": [Equipment, Equipment, ...],  # Seed + companions
    "shared_resources_count": 5,                # Resources in ALL items
    "sharing_efficiency": 0.45,                 # Reuse ratio
    "total_ingredients": {                      # Aggregated recipe
        123: 45,                                # Resource ID: quantity
        456: 30,
        ...
    },
    "selection_method": "random",               # NEW
    "seed_equipment_id": 12345,                 # NEW: Seed equipment ID
    "randomness_seed": 42,                      # NEW: RNG seed for reproducibility
}
```

### Deterministic Group Object (Unchanged)
```
Group = {
    "equipments": [Equipment, ...],
    "shared_resources_count": 5,
    "sharing_efficiency": 0.45,
    "total_ingredients": {...},
    "selection_method": "deterministic",        # NEW: Always present
    # No seed_equipment_id or randomness_seed
}
```

---

## Integration Points

### 1. Config Override Chain
```
config.py (defaults)
    ↓
ProcessingConfig (dataclass, can override)
    ↓
CLI arguments (highest priority)
```

### 2. Grouping Method Dispatch
```
main.py process_equipment()
    ├─ if "deterministic": master.run_all()
    ├─ if "random": master.run_random_grouping()
    └─ if "hybrid": master.run_hybrid_grouping()
```

### 3. Filtering Strategy Usage
```
run_random_grouping()
    └─ EquipmentFilteringStrategy.get_active_pool()
        ├─ Filter by density
        └─ Fallback if needed

run_hybrid_grouping()
    └─ EquipmentFilteringStrategy.get_active_pool()
        ├─ For random groups only
        └─ Deterministic uses all equipment
```

---

## Testing Checklist

- [x] All files have valid Python syntax
- [ ] Can instantiate EquipmentFilteringStrategy
- [ ] Filter returns correct subset of equipment
- [ ] Fallback logic works when pool too small
- [ ] RandomGroupBuilder builds valid groups
- [ ] Seed selection is random
- [ ] Companions share resources with seed
- [ ] Multiple groups avoid seed duplicates
- [ ] RuneMaster.run_random_grouping() works
- [ ] RuneMaster.run_hybrid_grouping() works
- [ ] CLI arguments parsed correctly
- [ ] Groups have all required fields
- [ ] Visualization still works with new groups
- [ ] Deterministic mode unchanged

