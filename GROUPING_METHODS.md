"""# Grouping Methods Guide

This guide explains each grouping method available in RuneMaster, their design,
trade-offs, and when to use each one.

## Overview

RuneMaster provides six distinct strategies for discovering equipment groups.
All methods share the same fundamental goal—finding sets of equipment whose
recipes share resources—but differ in how they search the solution space and
trade speed for result quality.

### Method Selection Cheat Sheet

| Your Priority | Recommended Method |
| --- | --- |
| Best possible groups | `evolutionary_committee` |
| Fast, still very good | `committee` |
| Fastest iteration | `deterministic` |
| Exploring diversity | `random` |
| Single-expert deep dive | `genetic` |
| Reliable fallback | `hybrid` |

---

## Detailed Method Descriptions

### 1. Deterministic (Graph-Based)

**Algorithm**: Similarity graph → Louvain community detection

**How it works**:
1. Build equipment similarity graph (Jaccard similarity on recipe resources)
2. Apply configurable edge thresholds (`graph_min_shared_ratio`, `graph_min_shared_count`)
3. Run community detection (Louvain, BiLouvain, or connected components)
4. Map communities to equipment groups

**Characteristics**:
- ✅ **Reproducible**: Same input always produces same output
- ✅ **Fast**: ~milliseconds for typical dataset
- ✅ **Transparent**: Easy to inspect and understand
- ❌ Assumes graph structure reflects good groups
- ❌ Misses non-contiguous but compatible equipment
- ⚠️ Quality depends heavily on edge thresholds

**Best for**:
- Development and testing
- Quick parameter exploration
- Understanding baseline grouping
- Fully deterministic workflows

**Example**:
```bash
make method METHOD=deterministic
uv run main.py --grouping-method deterministic --no-serve
```

**Configuration**:
```python
config.graph_min_shared_ratio = 0.3      # Min Jaccard similarity
config.graph_min_shared_count = 1        # Min absolute shared resources
config.algorithm = "louvain"             # Detection algorithm
```

---

### 2. Random (Stochastic Sampling)

**Algorithm**: Density filtering → seed selection → greedy companion finding

**How it works**:
1. Apply density filtering (optional, for equipment quality)
2. Randomly sample unique equipment as group seeds
3. For each seed, greedily add compatible companions
4. Repeat until target group count reached

**Characteristics**:
- ✅ **Diverse**: Different runs produce different solutions
- ✅ **Flexible**: Can generate many solutions for analysis
- ✅ **Fast**: ~milliseconds to seconds
- ❌ Greedy (quality depends on seed order)
- ❌ Target count is not guaranteed
- ⚠️ Results vary with random seed

**Best for**:
- Exploring multiple solution possibilities
- Checking solution robustness
- Understanding variability in grouping
- Diversity-oriented analysis

**Example**:
```bash
uv run main.py --grouping-method random --random-groups 50 --no-serve
```

**Configuration**:
```python
config.random_group_count = 50           # Target groups (not guaranteed)
config.random_seed = 42                  # For reproducibility
config.use_density_filtering = True      # Filter by equipment density
```

---

### 3. Hybrid (Deterministic + Random Fallback)

**Algorithm**: Deterministic first, supplement with random if needed

**How it works**:
1. Run deterministic (graph-based) grouping
2. If result has fewer groups than threshold (`max(5, random_group_count / 2)`):
   - Run random grouping to supplement
   - Combine both results
3. Otherwise, return deterministic result only

**Characteristics**:
- ✅ **Balanced**: Usually deterministic, can supplement with diversity
- ✅ **Fast**: Same speed as deterministic unless supplementing
- ✅ **Safe**: Guaranteed coverage via random fallback
- ⚠️ Quality depends on whether threshold is reached
- ⚠️ Mixes two different strategies

**Best for**:
- Production pipelines needing reliability
- Scenarios where deterministic alone might be sparse
- Balanced speed/quality without full evolution

**Example**:
```bash
make method METHOD=hybrid
uv run main.py --grouping-method hybrid --no-serve
```

**Configuration**:
```python
config.grouping_method = "hybrid"
config.random_group_count = 50
# Uses both deterministic + random config
```

---

### 4. Committee (Multi-Expert Consensus)

**Algorithm**: Run all experts once, aggregate, deduplicate

**How it works**:
1. Pre-compute shared graph and resources
2. Run deterministic, random, and genetic experts in parallel
3. Score each proposal using canonical objective
4. Sort by score (highest first)
5. Greedy deduplication: keep groups if overlap < threshold
6. Report expert failures without blocking

**Characteristics**:
- ✅ **Multi-expert**: Combines strengths of all algorithms
- ✅ **Robust**: Expert failures don't block others
- ✅ **Good quality**: Usually very good results
- ✅ **Single pass**: Fast (~seconds)
- ⚠️ Static ensemble (no iteration)
- ⚠️ First-pass greedy deduplication

**Best for**:
- Fast multi-expert consensus
- Production pipelines
- Cases where single pass suffices
- Robust error handling needed

**Example**:
```bash
make method METHOD=committee
uv run main.py --grouping-method committee --no-serve
```

**Configuration**:
```python
config.grouping_method = "committee"
config.dedup_overlap_threshold = 0.7     # Jaccard threshold for duplicates
```

---

### 5. Genetic (Single-Expert Evolution)

**Algorithm**: Population-based evolutionary search within one expert

**How it works**:
1. Initialize population of group sets
2. For each generation (configurable rounds):
   - Evaluate fitness (group quality + overlap penalty)
   - Track best ever
   - Preserve elite (top N individuals)
   - Create new generation via:
     - Tournament selection
     - Crossover (blend two parents)
     - Mutation (add/remove/swap equipment, split/merge groups)
3. Stop on stagnation or max generations

**Characteristics**:
- ✅ **Focused**: Single expert, deep evolution
- ✅ **Good quality**: Decent results through iteration
- ⚠️ Single expert only
- ⚠️ Slower than committee (~10+ seconds)
- ⚠️ Limited to one search strategy
- ❌ Can get stuck in local optima

**Best for**:
- Deep dive on genetic/evolutionary approach
- Understanding mutation operators
- Focused search on group quality
- Contrasting with other methods

**Example**:
```bash
make method METHOD=genetic
uv run main.py --grouping-method genetic --no-serve
```

**Configuration**:
```python
config.genetic_population_size = 30
config.genetic_generations = 50
config.genetic_mutation_rate = 0.3
config.genetic_elite_count = 3
config.genetic_stagnation_limit = 15
```

---

### 6. Evolutionary Committee (Multi-Expert Iteration) — NEW, DEFAULT

**Algorithm**: Committee proposals → multi-round portfolio evolution

**How it works**:
1. Gather initial proposals from all experts (committee)
2. Initialize population from proposals + warm starts + cold starts
3. For each evolution round (configurable, default 5):
   - Evaluate all candidates using portfolio-level fitness
   - Update archive (global candidate tracking)
   - Preserve elite candidates
   - Inject diversity via cold-start portfolios
   - Create next generation via:
     - **Tournament selection** (pick best parents)
     - **Portfolio crossover** (blend parent portfolios)
     - **Portfolio mutation** (apply intelligent operators):
       - Add equipment to group (graph neighbor)
       - Remove weakest equipment
       - Swap for graph neighbor
       - Split oversized group
       - Merge compatible groups
       - Move equipment between groups
4. Return best portfolio found

**Key Differences from Genetic**:
- **Portfolio-level fitness** (not just group sum):
  - Rewards coverage
  - Penalizes duplicate assignments
  - Balances group quality with diversity
  - Ensures non-redundant final result
- **Multi-expert initial proposals**
- **Iterative rounds** (can improve across rounds)
- **Warm-start support** (seed from prior portfolios)
- **Archive tracking** (remember all good candidates)
- **Stagnation detection** (stop early if no improvement)

**Characteristics**:
- ✅ **Best quality**: Multi-round portfolio optimization
- ✅ **Multi-expert**: Starts from committee proposals
- ✅ **Portfolio-aware**: Optimizes coverage and balance, not just group scores
- ✅ **Diverse operators**: Smart mutation strategies
- ✅ **Reproducible**: Deterministic with fixed seed
- ✅ **Warm-start capable**: Can seed from prior results
- ⚠️ **Slower**: ~1-5 minutes depending on equipment pool
- ⚠️ More parameters to tune

**Best for**:
- **Production pipelines needing best results**
- **Thorough analysis and reports**
- **Cases where quality > speed**
- **Reproducible, auditable grouping**
- **Seeding from prior knowledge (warm start)**

**Example**:
```bash
make compute                                  # Default, best results
uv run main.py --grouping-method evolutionary_committee --no-serve
```

**Configuration**:
```python
config.evolutionary_enabled = True           # Enable evolutionary search
config.evolutionary_rounds = 5               # Number of evolution rounds
config.evolutionary_population_size = 30     # Population per round
config.evolutionary_elite_count = 5          # Best to preserve
config.evolutionary_mutation_rate = 0.4      # Mutation probability
config.evolutionary_crossover_rate = 0.6     # Crossover probability
config.evolutionary_cold_start_fraction = 0.2  # Diversity injection
config.evolutionary_archive_size = 200       # Candidate archive
config.evolutionary_stagnation_limit = 3     # Stop if no improvement
config.evolutionary_random_seed = None       # Reproducibility
config.evolutionary_warm_start_enabled = False  # Seed from prior
```

---

## Comparison Table

| Feature | Deterministic | Random | Hybrid | Committee | Genetic | Evolutionary Committee |
| --- | --- | --- | --- | --- | --- | --- |
| **Speed** | ⚡⚡⚡ | ⚡⚡ | ⚡⚡ | ⚡⚡ | ⚡ | 🐢 |
| **Quality** | Good | Fair | Good | ⭐ V.Good | ⭐ V.Good | ⭐⭐⭐ Excellent |
| **Reproducible** | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Multi-expert** | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| **Iterative** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Portfolio-aware** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Warm-start** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Easy to tune** | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐ |

---

## Performance Benchmarks

Approximate runtimes on 300-500 equipment:

| Method | Time | Notes |
| --- | --- | --- |
| Deterministic | 100ms | Graph building + community detection |
| Random | 200-500ms | Depends on group count target |
| Hybrid | 200-500ms | Usually deterministic only |
| Committee | 2-5s | Parallel expert execution |
| Genetic | 10-30s | 50 generations × 30 population |
| Evolutionary Committee | 30-120s | 5 rounds × 30 population × expert overhead |

Times are wall-clock, single-threaded, excluding API calls and cache operations.

---

## How to Choose

### Quick Decision Tree

```
Are you in development/testing?
  ↓ YES → Use DETERMINISTIC (or HYBRID)
  ↓ NO
        Do you want the best possible groups?
          ↓ YES → Use EVOLUTIONARY_COMMITTEE (patience required)
          ↓ NO
                Do you need fast results?
                  ↓ YES → Use COMMITTEE
                  ↓ NO → Use GENETIC or COMMITTEE
```

### Recommendations by Workflow

**Daily reporting / Production**
```bash
make compute  # Evolutionary committee for best quality
```

**Development / Quick iterations**
```bash
make method METHOD=hybrid  # Fast with fallback coverage
# or
make method METHOD=deterministic  # Fastest
```

**Exploration / Understanding**
```bash
uv run main.py --grouping-method random      # See diversity
uv run main.py --grouping-method deterministic  # See baseline
uv run main.py --grouping-method committee  # See consensus
```

**Thorough analysis**
```bash
# Run multiple methods and compare
make method METHOD=committee
make method METHOD=evolutionary_committee
# Compare results in visualization dashboard
```

---

## Tuning Tips

### Speed Up Evolutionary Committee

If evolutionary committee is too slow:

```python
config.evolutionary_rounds = 2          # Fewer rounds (was 5)
config.evolutionary_population_size = 15  # Smaller population (was 30)
config.evolutionary_elite_count = 2     # Fewer elite (was 5)
```

This trades quality for ~3-5x speedup.

### Improve Committee Quality

To get better committee results without full evolution:

```python
config.dedup_overlap_threshold = 0.5    # Stricter deduplication (was 0.7)
config.genetic_generations = 75         # Deeper genetic search (was 50)
```

### Reproducible Randomness

For fully reproducible runs across environments:

```python
config.random_seed = 42
config.evolutionary_random_seed = 42
config.grouping_method = "evolutionary_committee"
```

---

## Architecture Notes

All methods ultimately produce the same output format:
- List of group dictionaries
- Each group has equipment list, quality metrics, sharing efficiency
- Canonical fitness scoring via shared `GroupObjective`
- Final deduplication via shared `PortfolioSelector`

The methods differ only in **how groups are discovered**, not in:
- How they're evaluated
- How they're validated
- How they're deduplicated
- How they're reported

This allows fair comparison and smooth method switching without changing output contracts.
"""
