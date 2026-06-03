# Rune Master - Practical Refactoring Plan (UPDATED)

**Status**: 30% Complete - Structure in place, implementation incomplete
**Date**: January 16, 2026

---

## Executive Summary

Your project **has the right structure** but the modules are **mostly empty stubs**. This plan prioritizes:
1. **Migrating code from OLD/** to new structure (HIGH PRIORITY)
2. **Filling empty modules** with actual implementation
3. **Removing circular dependencies** and OLD/ directory
4. **Achieving working state** before optimization

---

## Current State Assessment

### ✅ What's Good
- Directory structure is clean and well-organized
- Separation of concerns is conceptually correct:
  - `models/` - Data structures
  - `data/` - API + caching
  - `processing/` - Algorithms
  - `optimization/` - Resource calculations
  - `visualization/` - HTML generation
- No circular imports in new code (because there's no code yet!)

### ⚠️ What's Problematic
| Issue | Severity | Files |
|-------|----------|-------|
| **Empty stub files** | CRITICAL | `data/api_client.py`, `data/loaders.py`, `processing/graph_builder.py`, `processing/group_mapper.py`, `processing/community_detector.py` |
| **Code in OLD/** | CRITICAL | `OLD/app.py`, `OLD/models.py`, `OLD/services/` (actual implementation) |
| **Empty main.py** | CRITICAL | No entry point |
| **Dual config** | HIGH | Config in both `/config.py` and `OLD/config.py` |
| **No integration** | HIGH | New modules not connected to each other |
| **Orphaned OLD/** | MEDIUM | Dead code consuming space |

### 📊 Code Distribution
```
Active code:     models/equipment.py (92 lines)
Stub modules:    ~2000 lines of empty files
Legacy code:     OLD/ directory (~5000 lines - needs migration)
```

---

## Corrected Refactoring Plan

### Phase 1: Audit & Extract (Week 1)

**Goal**: Understand what's in OLD/, decide what to keep

#### 1.1 Analyze OLD/ Code
```bash
# In terminal:
wc -l OLD/**/*.py          # Count lines
find OLD -name "*.py" | sort
```

**Action Items**:
- [ ] Read `OLD/models.py` - what data models exist?
- [ ] Read `OLD/app.py` - what's the main entry point logic?
- [ ] Read `OLD/services/graph/dataprocessor.py` - complex algorithms?
- [ ] Read `OLD/config.py` - config differences vs new `config.py`?
- [ ] Read `OLD/provider/dofusapi.py` - API client implementation?

**Decision**: For each file, decide: **MIGRATE | REWRITE | KEEP**

---

### Phase 2: Migrate Code (Week 1-2)

**Goal**: Move OLD/ code into new structure, keep it working

#### 2.1 Models Migration
**Source**: `OLD/models.py`
**Target**: `models/{equipment.py, resource.py, recipe.py}`
**Status**: Partially done (equipment.py has 92 lines)

**Tasks**:
- [ ] Complete `models/equipment.py` with all Equipment class logic
- [ ] Create `models/resource.py` from OLD (Resource dataclass)
- [ ] Create `models/recipe.py` (ResourceRequirement dataclass)
- [ ] Create `models/__init__.py` exports (all public dataclasses)
- [ ] Ensure NO business logic in models (only `@dataclass` fields + property getters)

**CheckList**:
```python
# ✅ Good - Properties only
@property
def stat_name(self) -> str:
    return self.stat_type['name']

# ❌ Bad - Business logic in model
def compute_stat_weight(self) -> float:
    return sum(...)  # Move to loaders.py
```

---

#### 2.2 Data Layer Migration
**Source**: `OLD/provider/dofusapi.py`, `OLD/cache_manager.py` (if exists), `OLD/utils.py`
**Target**: `data/{api_client.py, cache_manager.py, loaders.py}`

##### 2.2a api_client.py
**Responsibilities**:
- API HTTP calls to dofusapi
- Convert raw JSON to intermediate dicts
- Handle API errors

**File Checklist**:
```python
class DofusAPIClient:
    """Low-level API communication - NO conversion to dataclasses"""
    
    def __init__(self, game: str = 'dofus3', language: str = 'fr')
    
    def get_equipment(self, ankama_id: int) -> dict:
        """Raw API response, no conversion"""
    
    def list_equipment_ids(self, item_type: str, level_range: tuple) -> List[int]:
    
    def get_resource(self, ankama_id: int) -> dict:
    
    def batch_get_equipments(self, ankama_ids: List[int]) -> List[dict]:
    
    def search_equipments(self, filters: dict) -> List[dict]:
```

**Status**: Currently empty

##### 2.2b cache_manager.py
**Responsibilities**:
- Load/save cache files
- Simple dict operations (no API calls)
- Cache invalidation

**File Checklist**:
```python
class CacheManager:
    """Persistent disk cache - JSON serialization only"""
    
    def __init__(self, cache_file: str = 'resource_cache.json')
    
    def load_cache(self) -> dict:
        """Load from disk"""
    
    def save_cache(self, data: dict) -> None:
    
    def has_resource(self, resource_id: int) -> bool:
    
    def get_resource_info(self, resource_id: int) -> dict:
    
    def add_resource(self, resource_id: int, data: dict) -> None:
    
    def is_stale(self, max_age_hours: int = 24) -> bool:
```

**Status**: Currently empty

##### 2.2c loaders.py
**Responsibilities**:
- Convert raw API dicts → dataclasses
- Equipment-specific transformations
- Static utility functions (no dependencies on other loaders)

**File Checklist**:
```python
class EquipmentLoader:
    """Pure transformation: dict → Equipment dataclass"""
    
    @staticmethod
    def from_raw_api(raw: dict, cache: CacheManager = None) -> Equipment:
        """Convert API response to Equipment dataclass"""
    
    @staticmethod
    def compute_stat_weight(effects: List[EquipmentStat]) -> float:
        """Stat importance calculation (moved from Equipment model)"""
    
    @staticmethod
    def enrich_with_cache(equipment: Equipment, cache: CacheManager) -> Equipment:
        """Add cached resource names to recipe"""

class ResourceLoader:
    @staticmethod
    def from_raw_api(raw: dict) -> Resource:
    
class RecipeLoader:
    @staticmethod
    def from_raw_api(raw: dict) -> List[ResourceRequirement]:
```

**Status**: Currently empty

---

#### 2.3 Processing Layer Migration
**Source**: `OLD/services/graph/dataprocessor.py` (large, complex file)
**Target**: `processing/{graph_builder.py, community_detector.py, group_mapper.py, data_processor.py}`

**Status**: All 4 files currently EMPTY

**This is the most complex part.** Each module needs extraction from OLD/dataprocessor.py:

##### 2.3a graph_builder.py
**Extract from DataProcessor methods**:
- `create_bipartite_graph()`
- `create_jaccard_similarity_graph()`
- `get_equipment_resources()`
- `remove_weak_components()`

**File Template**:
```python
class GraphBuilder:
    """Build equipment relationship graphs"""
    
    def create_bipartite_graph(
        self,
        equipments: List[Equipment]
    ) -> nx.Graph:
        """Equipment ↔ Resource bipartite graph"""
    
    def create_jaccard_similarity_graph(
        self,
        equipment_resources: Dict[int, set]
    ) -> nx.Graph:
        """Equipment similarity based on shared recipes"""
    
    def get_equipment_resources(
        self,
        graph: nx.Graph
    ) -> Dict[int, set]:
        """Extract resource sets for each equipment"""
    
    def remove_weak_components(
        self,
        graph: nx.Graph,
        min_size: int = 2
    ) -> nx.Graph:
```

**Status**: EMPTY - needs extraction

##### 2.3b community_detector.py
**Extract from DataProcessor methods**:
- `find_best_partition()`
- `find_communities_optimized_for_bulk()`
- `_evaluate_partition_quality()` (helper)

**File Template**:
```python
class CommunityDetector:
    """Detect equipment communities using Louvain algorithm"""
    
    def find_best_partition(
        self,
        graph: nx.Graph,
        resolution_range: Tuple[float, float] = (0.5, 2.0),
        target_community_size: int = 3
    ) -> Dict[int, int]:
        """Find partition with best modularity"""
    
    def find_communities_optimized_for_bulk(
        self,
        bipartite_graph: nx.Graph,
        equipment_nodes: set,
        target_community_size: int = 3,
        resolution_range: Tuple[float, float] = (0.5, 2.0)
    ) -> Dict[int, List[int]]:
```

**Status**: EMPTY - needs extraction

##### 2.3c group_mapper.py
**Extract from DataProcessor methods**:
- `map_communities()`
- `calculate_total_ingredients()`
- `calculate_shared_resources()`
- `_resolve_equipment_objects()` (helper)

**File Template**:
```python
class GroupMapper:
    """Convert detected communities → optimized equipment groups"""
    
    def map_communities(
        self,
        communities: Dict[int, List[int]],
        equipment_dict: Dict[int, Equipment],
        min_shared_resources: int = 2,
        efficiency_threshold: float = 0.3,
        excluded_resource_ids: Set[int] = None
    ) -> List[Dict]:
        """Create group metrics and metadata"""
    
    def calculate_total_ingredients(
        self,
        group_equipments: List[Equipment]
    ) -> Dict[int, Dict]:
        """Aggregate recipe costs"""
    
    def calculate_shared_resources(
        self,
        group_equipments: List[Equipment],
        excluded_resource_ids: Set[int] = None
    ) -> Tuple[int, int, float]:
        """Efficiency metrics"""
```

**Status**: EMPTY - needs extraction

##### 2.3d data_processor.py (Orchestrator)
**Keep simple** - coordinates the above 3 classes

**File Template**:
```python
class DataProcessor:
    """Orchestrator - coordinates graph, detection, and mapping"""
    
    def __init__(
        self,
        equipments: List[Equipment],
        graph_builder: GraphBuilder = None,
        community_detector: CommunityDetector = None,
        group_mapper: GroupMapper = None,
        excluded_resource_ids: Set[int] = None
    ):
    
    def find_equipment_groups(
        self,
        resolution: float = 1.0,
        target_community_size: int = 3,
        min_shared_resources: int = 2
    ) -> List[Dict]:
        """Main orchestration method"""
        # 1. Build graph
        # 2. Detect communities
        # 3. Map to groups
        # 4. Return results
    
    @classmethod
    def find_optimized_equipment_groups(
        cls,
        equipments: List[Equipment],
        **kwargs
    ) -> List[Dict]:
        """Factory method for simple usage"""
```

**Status**: EMPTY - needs creation

---

#### 2.4 Optimization Layer
**Source**: `OLD/services/optimizer/resourceoptimizer.py` (if exists)
**Target**: `optimization/resource_optimizer.py`

**Status**: Likely EMPTY or minimal

**Responsibilities**:
- Calculate purchasing decisions for equipment groups
- Minimize resource overlap
- Optimize bulk purchases

---

#### 2.5 Visualization Layer
**Source**: `OLD/services/visualizer/`, `OLD/app.py` visualization code
**Target**: `visualization/`

**Status**: Directory structure in place, content EMPTY

**Files to create**:
- `visualization/html_generator.py` - D3.js + HTML generation
- `visualization/style_templates.py` - CSS templates
- `visualization/index_builder.py` - Index page generation
- `visualization/templates/` - HTML/CSS templates

---

### Phase 3: Configuration Consolidation (Week 1)

**Current**: Two config files
```
config.py              (New, partial)
OLD/config.py         (Old, complete)
```

**Task**: Merge into unified `config.py`

**Actions**:
- [ ] Read both files
- [ ] Identify differences
- [ ] Create unified config with all needed values
- [ ] Add detailed comments
- [ ] Delete OLD/config.py

**Target config.py structure**:
```python
from dataclasses import dataclass
from typing import Set, List

@dataclass
class APIConfig:
    """Dofus API settings"""
    GAME: str = 'dofus3'
    LANGUAGE: str = 'fr'
    API_BASE_URL: str = 'https://api.dofusdu.de'
    TIMEOUT_SECONDS: int = 30

@dataclass  
class CacheConfig:
    """Cache settings"""
    CACHE_FILE: str = 'resource_cache.json'
    CACHE_DIR: str = './cache'
    MAX_AGE_HOURS: int = 24

@dataclass
class ProcessingConfig:
    """Algorithm settings"""
    MIN_LEVEL: int = 20
    MAX_LEVEL: int = 60
    MIN_CLUSTER_SIZE: int = 2
    MIN_COMMON_ITEMS: int = 3
    MIN_SIMILARITY: float = 0.3
    RESOLUTION_RANGE: tuple = (0.5, 2.0)
    TARGET_COMMUNITY_SIZE: int = 3

@dataclass
class ExclusionConfig:
    """Items to exclude from analysis"""
    EXCLUDED_RESOURCES: Set[int] = None
    EXCLUDED_ITEM_TYPES: Set[str] = None
    
    def __post_init__(self):
        if self.EXCLUDED_RESOURCES is None:
            self.EXCLUDED_RESOURCES = {15263, 14635}

@dataclass
class OutputConfig:
    """Output settings"""
    REPORTS_DIR: str = './reports'
    VISUALIZATION_DIR: str = './visualizations'
    OUTPUT_PREFIX: str = 'crafting_groups'
    SORT_BY: str = 'level'
    SORT_ORDER: str = 'desc'

# Single access point
class Config:
    api = APIConfig()
    cache = CacheConfig()
    processing = ProcessingConfig()
    exclusion = ExclusionConfig()
    output = OutputConfig()
```

---

### Phase 4: Integration Tests (Week 2)

**Goal**: Get complete pipeline working end-to-end

#### 4.1 Create main.py Entry Point
```python
# main.py
"""Main entry point - orchestrates the full pipeline"""

from data.api_client import DofusAPIClient
from data.cache_manager import CacheManager
from data.loaders import EquipmentLoader
from processing.data_processor import DataProcessor
from visualization.html_generator import VisualizationEngine
from config import Config

def main():
    # 1. Fetch equipments
    api = DofusAPIClient(Config.api.GAME, Config.api.LANGUAGE)
    cache = CacheManager(Config.cache.CACHE_FILE)
    
    equipments = fetch_equipments(api, cache)
    
    # 2. Process
    processor = DataProcessor(equipments, Config.exclusion.EXCLUDED_RESOURCES)
    groups = processor.find_equipment_groups()
    
    # 3. Visualize
    visualizer = VisualizationEngine(Config.output.VISUALIZATION_DIR)
    visualizer.generate_group_visualization(groups)
    
    print(f"Generated {len(groups)} equipment groups")

if __name__ == '__main__':
    main()
```

#### 4.2 Test Notebooks
- [ ] Run existing notebooks with new import paths
- [ ] Fix any import errors
- [ ] Verify output consistency

---

### Phase 5: Cleanup (Week 2)

**Goal**: Remove OLD/, achieve production-ready state

**Actions**:
- [ ] Move any remaining useful code from OLD/
- [ ] Delete OLD/ directory entirely
- [ ] Update .gitignore
- [ ] Create MIGRATION_COMPLETE.md documenting what moved where
- [ ] Archive OLD/ as git commit (before deletion)

---

## Priority Order (Practical Execution)

### Week 1 - Foundation
1. **Audit** `OLD/` - understand all code (Day 1)
2. **Complete models/** - all Equipment, Resource, Recipe dataclasses (Day 1-2)
3. **Fill data layer** - api_client.py, cache_manager.py, loaders.py (Day 2-3)
4. **Merge config** - unified configuration (Day 3)
5. **Quick test** - can we import all modules? (Day 4)

### Week 2 - Processing Logic
1. **Extract graph algorithms** - graph_builder.py from OLD (Day 1-2)
2. **Extract community detection** - community_detector.py (Day 2)
3. **Extract group mapping** - group_mapper.py (Day 3)
4. **Create orchestrator** - data_processor.py (Day 3)
5. **Integration test** - main.py works end-to-end (Day 4)

### Week 3 - Visualization & Cleanup
1. **Migrate visualization** - html_generator.py, templates (Day 1-2)
2. **Delete OLD/** - clean up dead code (Day 2)
3. **Fix notebooks** - update all imports (Day 3)
4. **Final testing** - full pipeline validation (Day 4)

---

## Critical Dependencies

```
models/                (Foundation - needs NO dependencies)
  ├── equipment.py
  ├── resource.py
  └── recipe.py

data/                  (Depends on: models)
  ├── api_client.py    (Pure API - no dependencies)
  ├── cache_manager.py (File I/O - no dependencies)
  └── loaders.py       (Depends on: models)

processing/            (Depends on: models, data)
  ├── graph_builder.py
  ├── community_detector.py
  ├── group_mapper.py
  └── data_processor.py (Depends on: all above)

optimization/          (Depends on: models, processing)
  └── resource_optimizer.py

visualization/         (Depends on: models, processing)
  ├── html_generator.py
  └── templates/

main.py               (Depends on: everything)
```

**Rule**: Always build bottom-up (models → data → processing → optimization → visualization → main)

---

## File Inventory

### Create/Fill (15 files)
```
✏️  models/__init__.py          (exports)
✏️  models/equipment.py         (partial - complete it)
✏️  models/resource.py          (new)
✏️  models/recipe.py            (new)

✏️  data/__init__.py            (exports)
✏️  data/api_client.py          (empty - fill from OLD)
✏️  data/cache_manager.py       (empty - fill from OLD)
✏️  data/loaders.py             (empty - create)

✏️  processing/__init__.py       (exports)
✏️  processing/graph_builder.py (empty - extract)
✏️  processing/community_detector.py (empty - extract)
✏️  processing/group_mapper.py  (empty - extract)
✏️  processing/data_processor.py (empty - create orchestrator)

✏️  config.py                   (update - merge configs)
✏️  main.py                     (empty - create entry point)
```

### Delete (1 directory)
```
🗑️  OLD/                         (Move to archive, then delete)
```

### Keep As-Is (existing working files)
```
✅  models/common.py            (type hints - keep)
✅  optimization/resource_optimizer.py (if complete)
✅  visualization/__init__.py   (keep)
```

---

## Success Criteria

- [ ] All 15 new files created and filled with implementation
- [ ] No empty stub files (except __init__.py)
- [ ] `python main.py` runs without errors
- [ ] All notebooks run with new import paths
- [ ] OLD/ directory deleted
- [ ] Code organized by single responsibility
- [ ] No circular imports
- [ ] Clear dependency flow (bottom-up)
- [ ] All config in one place
- [ ] Production-ready state

---

## Risk Mitigation

| Risk | Prevention |
|------|-----------|
| Breaking existing code | Keep OLD/ until Week 3, run notebooks after each phase |
| Circular imports | Always build bottom-up, test imports frequently |
| Missing edge cases | Unit test each module during extraction |
| Performance drop | Profile after each phase |
| Incomplete migration | Create MIGRATION_COMPLETE.md tracking moved code |

---

## Next Steps

1. **TODAY**: Run audit script to understand OLD/ codebase
2. **TOMORROW**: Start with models/ - the foundation
3. **This week**: Get data layer working
4. **Next week**: Process pipeline
5. **Week 3**: Finish, cleanup, delete OLD/

Would you like me to start with Step 1 (auditing OLD/) or a specific module?
