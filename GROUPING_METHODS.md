# Grouping Methods Guide

This guide explains each grouping method available in RuneMaster, their design,
trade-offs, and when to use each one. The authoritative functional spec is
`processing/PROCESSING.md`; this file is a user-level comparison.

## Overview

RuneMaster provides five strategies for discovering equipment groups. All share
the same goal — finding sets of equipment whose recipes share resources — but
differ in how they search the solution space and trade speed for quality.

### Method Selection Cheat Sheet

| Your Priority | Recommended Method |
| --- | --- |
| Best quality/coverage/speed | `greedy` (default) |
| Fastest iteration | `deterministic` |
| Reliable fallback | `hybrid` |
| Exploring diversity | `random` |
| Union of every expert | `survey` |

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
- Reproducible: same input always produces the same output
- Fast: ~milliseconds for a typical dataset
- Transparent: easy to inspect and understand
- Assumes graph structure reflects good groups
- Misses non-contiguous but compatible equipment

**Best for**: development, quick parameter exploration, fully deterministic workflows.

```bash
make method METHOD=deterministic
uv run main.py --grouping-method deterministic --no-serve
```

```python
config.graph_min_shared_ratio = 0.15     # Min Jaccard similarity
config.graph_min_shared_count = 1        # Min absolute shared resources
config.algorithm = "louvain"             # Detection algorithm
```

---

### 2. Random (Stochastic Sampling)

**Algorithm**: Density filtering → seed selection → greedy companion finding

**How it works**:
1. Apply density filtering (optional)
2. Randomly sample unique equipment as group seeds
3. For each seed, greedily add compatible companions
4. Repeat until the target group count is reached or seeds run out

**Characteristics**:
- Diverse: different runs produce different solutions
- Fast: ~milliseconds to seconds
- Greedy (quality depends on seed order)
- Target count is a target, not a guarantee

**Best for**: exploring multiple solutions, checking robustness, diversity-oriented analysis.

```bash
uv run main.py --grouping-method random --random-groups 50 --no-serve
```

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
2. If the result has fewer groups than `max(5, random_group_count / 2)`, run random grouping and concatenate
3. Otherwise return the deterministic result only

**Characteristics**:
- Balanced: usually deterministic, can supplement with diversity
- Fast: same speed as deterministic unless supplementing
- No cross-source sorting or de-duplication

**Best for**: scenarios where deterministic alone might be sparse.

```bash
make method METHOD=hybrid
uv run main.py --grouping-method hybrid --no-serve
```

---

### 4. Greedy (Objective-Driven) — DEFAULT

**Algorithm**: Seed from high-density uncovered items and grow each group
directly against the objective.

**How it works**:
1. Order items by break density (seeds)
2. For each uncovered seed, grow a group by repeatedly adding the companion the
   objective likes most, shortlisted by shared-resource count
3. Respect the panoplie set-share cap during growth
4. Keep groups disjoint; accept each against the common policy

**Characteristics**:
- Best quality/coverage/speed trade-off on every measured craft
- Reaches items the similarity graph discards
- Reproducible with a fixed `random_seed`

**Best for**: the default production run.

```bash
make evolve
uv run main.py --grouping-method greedy --no-serve
```

```python
config.greedy_candidate_limit = 25       # Candidates scored per growth step
config.greedy_seed_limit = 0             # Seeds to expand; 0 = whole pool
```

---

### 5. Survey (All Experts, Union of Proposals)

**Algorithm**: Run every expert and keep the union of their proposals.

**How it works**:
1. Build the shared graph once
2. Run each active expert (deterministic, random, greedy)
3. Merge identical equipment fingerprints, tagging each group with the
   expert(s) that proposed it (`origins` / `origin`)

**Characteristics**:
- Diagnostic: shows which experts find which groups
- Superset of the individual methods; no portfolio optimization

**Best for**: inspecting expert agreement and coverage.

```bash
make compute
uv run main.py --grouping-method survey --no-serve
```

---

## Comparison Table

| Feature | Deterministic | Random | Hybrid | Greedy | Survey |
| --- | --- | --- | --- | --- | --- |
| **Speed** | Fast | Fast | Fast | Fast | Fast |
| **Quality** | Good | Fair | Good | Very Good | Good |
| **Reproducible** | Yes | No | Yes | Yes | Yes |
| **Multi-expert** | No | No | No | No | Yes |
| **Reaches graph-discarded items** | No | Partly | Partly | Yes | Partly |

---

## How to Choose

```
Are you in development/testing?
  -> YES: DETERMINISTIC (or HYBRID)
  -> NO
        Want the best groups?
          -> YES: GREEDY (default)
          -> NO: RANDOM to explore, or SURVEY to see every expert's proposals
```

**Daily reporting / production**

```bash
make evolve   # Greedy, best quality/coverage/speed
```

**Development / quick iterations**

```bash
make method METHOD=deterministic  # Fastest
```

---

## Architecture Notes

All methods produce the same output contract: a list of canonical group
dictionaries (equipment list, quality metrics, sharing efficiency) built by
`GroupMetrics.build_group_dict()` and evaluated by the shared objective. The
methods differ only in **how groups are discovered**, not in how they are
evaluated, validated, or reported. This allows fair comparison and smooth
method switching.

Removed methods (`committee`, `genetic`, `evolutionary_committee`, `baseline`)
were measured as dominated by greedy — see `plans/phase1-decision.md`. Their
code has been deleted.
