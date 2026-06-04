# Plan 02: Cache Graph Construction Across Experts in Committee Mode

## Problem
In `run_committee()`, each expert independently calls `GraphBuilder.build_equipment_graph()` with the same input data, rebuilding the bipartite graph, extracting resources, and computing the Jaccard similarity graph from scratch. This happens **3 times** (Graph, Random, Genetic experts) — the most expensive O(n²) step is triplicated.

## Decision
Pre-compute the equipment graph and resource mappings once at the `RuneMaster` level in `run_committee()`, then pass them to experts via an optional context parameter. Experts use the cached data when available, falling back to building from scratch when called standalone.

## Atomic Actions

### Action 2.1: Add optional graph context parameters to `GroupingExpert.discover_groups`
- **File:** `processing/experts/base.py`
- **Lines:** L26-41 (`discover_groups` abstract method)
- **Change:** Add optional `precomputed_graph` and `precomputed_resources` parameters.
- **Details:**
  ```python
  @abstractmethod
  def discover_groups(
      self,
      equipments: List[Equipment],
      config: ProcessingConfig,
      precomputed_graph: Optional[nx.Graph] = None,
      precomputed_resources: Optional[Dict[int, Set[int]]] = None,
  ) -> List[Dict[str, Any]]:
  ```

### Action 2.2: Update `GraphGroupingExpert.discover_groups` to accept cached graph
- **File:** `processing/experts/graph_expert.py`
- **Lines:** L24-97 (`discover_groups` method)
- **Change:** Add `precomputed_graph` and `precomputed_resources` parameters. Use them when available, otherwise build from scratch.
- **Details:**
  - Signature: `def discover_groups(self, equipments, config, precomputed_graph=None, precomputed_resources=None)`
  - If both `precomputed_graph` and `precomputed_resources` are provided, skip `GraphBuilder.build_equipment_graph()` call
  - Otherwise, call `GraphBuilder.build_equipment_graph()` as before

### Action 2.3: Update `GeneticGroupingExpert.discover_groups` to accept cached graph
- **File:** `processing/experts/genetic_expert.py`
- **Lines:** L40-193 (`discover_groups` method)
- **Change:** Add `precomputed_graph` and `precomputed_resources` parameters. Use them when available.
- **Details:**
  - If both are provided, skip the `GraphBuilder.build_equipment_graph()` call at L50-55
  - Build `resource_sets` from `precomputed_resources` (applying excluded IDs filter)
  - Otherwise, build from scratch as before

### Action 2.4: Update `RandomGroupingExpert.discover_groups` signature (pass-through)
- **File:** `processing/experts/random_expert.py`
- **Lines:** L22-63 (`discover_groups` method)
- **Change:** Add `precomputed_graph=None, precomputed_resources=None` parameters to match the base class signature. These are unused by the random expert (it doesn't build a graph), but must accept them for polymorphism.
- **Details:** Add `**kwargs` or explicit unused parameters to maintain interface compatibility.

### Action 2.5: Update `RuneMaster.run_committee` to pre-compute and pass graph
- **File:** `processing/orchestrator.py`
- **Lines:** L100-148 (`run_committee` method)
- **Change:** Before dispatching to experts, build the graph once and pass it to each expert.
- **Details:**
  - Import `GraphBuilder` at the top of the file
  - Before the expert dispatch loop (L113), add:
    ```python
    # Pre-compute graph once for all experts
    from processing.graph_builder import GraphBuilder
    shared_graph, shared_resources = GraphBuilder.build_equipment_graph(
        self.equipments,
        min_shared_ratio=self.config.graph_min_shared_ratio,
        min_shared_count=self.config.group_min_shared_resources,
        min_component_size=self.config.graph_min_component_size,
    )
    ```
  - Pass to each expert: `expert.discover_groups(self.equipments, self.config, precomputed_graph=shared_graph, precomputed_resources=shared_resources)`

### Action 2.6: Add `nx.Graph` import to `base.py`
- **File:** `processing/experts/base.py`
- **Lines:** L1-8 (imports)
- **Change:** Add `from typing import TYPE_CHECKING` and conditional `import networkx as nx` for type hints, or use string annotation `"nx.Graph"`.
- **Details:** Use `Optional[Any]` or a forward reference to avoid adding `networkx` as a hard dependency of `base.py`.
