# Refactor Plan: Genetic and Evolutionary Groups

**Branch:** `refactor/genetic-evolutionary-review`  
**Worktree:** `/home/adamb/rune_master_worktrees/genetic-refactor`  
**Date:** 2026-10-10  
**Status:** PLAN — no code changes yet

---

## 1. Executive Summary

The genetic expert (`genetic_expert.py` + `genetic_operators.py`) and the evolutionary
committee (`evolutionary_search_engine.py` + `evolutionary_operators.py` +
`evolutionary_fitness.py` + `evolutionary_search_state.py`) are two of five grouping
experts in the pipeline. This plan challenges whether they are useful or should be
deleted, grounded in `plans/data-profile.md` and `plans/metrics-revision.md`.

**Bottom line:** Both are graph-bound stochastic search methods that operate on a
lossy projection of the resource-sharing structure. The data shows the graph is
sparse (6% of pairs share anything, median Jaccard 0.07) and that the genetic
expert is structurally redundant with the deterministic expert. The evolutionary
committee is the default method but its operators are entirely graph-bound with no
fallback to ungrouped items. We recommend a phased approach: measure first, fix the
committee's coverage, then decide on the genetic expert's fate.

---

## 2. What the Data Says

### 2.1 The graph is a lossy projection

From `data-profile.md`:

| Metric | Value | Implication |
|--------|-------|-------------|
| Total possible pairs | 4,082,653 | — |
| Candidate pairs (share >= 1 resource) | 246,081 | Only 6.03% of pairs share anything |
| Median Jaccard (candidate pairs) | 0.07 | Very low overlap even among candidates |
| P90 Jaccard | 0.18 | Even the top decile is sparse |
| Items with zero shared resources | 3,836,572 pairs | 94% of pairs are disconnected |

The graph is built at `graph_min_shared_ratio=0.15` (already lowered from 0.3 per
`config_dataclass.py:78`). At this threshold:

- Largest component: 2,807 items (98.2% of pool)
- 9 components total
- 51 items still isolated (2,858 - 2,807 = 51)

At the old threshold (0.3), 408 items (14.28%) had zero edges — invisible to all
graph-bound experts. The genetic expert was given a mutation fallback
(`_ungrouped_candidates` in `genetic_operators.py:122-158`) to address this, but
the evolutionary committee's operators were not.

### 2.2 The genetic expert is structurally redundant with deterministic

Both `GraphGroupingExpert` and `GeneticGroupingExpert`:

1. Build the same Jaccard graph (`GraphBuilder.build_equipment_graph`)
2. Are confined to `graph.nodes()` for seeding
3. Use `graph.neighbors()` for expansion
4. Share the same blind spot (items with no edges)

The genetic expert adds stochastic search (tournament selection, crossover,
mutation) but operates over the same graph-reachable set. The metrics-revision
(§3.7) notes: "deterministic and genetic are the same algorithm with different
search strategies over the same graph — they share the blind spot and will tend
to propose the same components."

### 2.3 The evolutionary committee is the default but graph-bound

`config_dataclass.py:12` declares `evolutionary_committee` as the default with
"excellent results" at 30-120s runtime. But every operator in
`evolutionary_operators.py` is graph-bound:

| Operator | Graph-bound? | Fallback? |
|----------|-------------|-----------|
| `add_equipment_to_group` | Yes — `graph.neighbors()` | No |
| `remove_weakest_equipment` | No (removes only) | N/A |
| `swap_equipment_for_neighbor` | Yes — `graph.neighbors()` | No |
| `split_oversized_group` | No (splits only) | N/A |
| `merge_compatible_groups` | No (merges only) | N/A |
| `move_equipment_between_groups` | No (moves only) | N/A |
| `cold_start_portfolio` | Yes — `graph.neighbors()` | No |

Three of seven operators cannot escape the graph. The cold-start operator — the
mechanism for diversity injection — is entirely graph-bound.

### 2.4 The greedy and baseline experts are the only full-coverage methods

`GreedyGroupingExpert` builds its own neighbor index from `recipe_resource_ids`
(`greedy_expert.py:49-54`) and `BaselineExpert` scans all equipments
(`baseline_expert.py:63-67`). Neither relies on the Jaccard graph. They reach items
the graph discards.

### 2.5 Runtime comparison

From `config_dataclass.py:6-12`:

| Method | Runtime | Coverage |
|--------|---------|----------|
| deterministic | ~100ms | Graph-bound |
| random | ~200-500ms | Full pool |
| hybrid | ~200-500ms | Graph + random fallback |
| committee | ~2-5s | Multi-expert consensus |
| genetic | ~10-30s | Graph-bound |
| evolutionary_committee | ~30-120s | Graph-bound (default) |

The two slowest methods are both graph-bound. The fastest full-coverage method
(greedy) is not the default.

---

## 3. Challenges to Current Design

### C1: The genetic expert adds cost without adding coverage

The genetic expert runs 50 generations of population-30 evolution (~10-30s) but
cannot reach items outside the graph. Its mutation fallback
(`_ungrouped_candidates`) was added to address this, but it only triggers when
`graph.neighbors()` returns nothing for a group — a narrow escape hatch. The
deterministic expert produces comparable groups in ~100ms.

**Question:** Does the stochastic search produce meaningfully better groups than
the deterministic expert on the same graph-reachable set? If not, it is pure
overhead.

### C2: The evolutionary committee's diversity mechanism is graph-bound

`cold_start_portfolio` is the diversity injection mechanism (20% of each
generation). It seeds from `graph.nodes()` and expands via `graph.neighbors()`.
This means the committee's diversity is confined to the graph-reachable set —
the same set the deterministic and genetic experts already cover. The committee
cannot discover novel groups outside the graph.

### C3: The default method is the slowest and most restrictive

`evolutionary_committee` is the default (`config_dataclass.py:12`) but is:
- The slowest method (30-120s)
- Graph-bound (cannot reach ~51 items at ratio 0.15)
- Dependent on expert proposals that are themselves graph-bound

### C4: The graph threshold change (0.3 -> 0.15) was made but not fully propagated

The config now uses 0.15, which shrinks the dead zone from 408 to ~51 items. But:
- The evolutionary committee's operators were never given an ungrouped fallback
- The genetic expert's fallback only triggers on empty neighbor sets
- No per-expert coverage reporting exists to verify the fix

---

## 4. Recommended Plan

### Phase 1: Measure before deleting (NO code changes)

**Goal:** Quantify the actual quality difference between methods on the full pool.

**Steps:**

1. Run `analysis_sweep.py` with all methods on the full 1-200 pool, recording:
   - `equipment_coverage_rate` per method
   - `portfolio_quality_score` per method
   - `mean_group_score` per method
   - Runtime per method
   - Per-expert coverage breakdown (which items each expert reaches)

2. Compare genetic vs deterministic on the graph-reachable set:
   - If genetic produces < 5% better quality, it is redundant
   - If genetic produces > 10% better quality, it has value as a refinement step

3. Compare evolutionary_committee vs committee:
   - If the evolutionary iteration adds < 5% quality, the extra runtime is unjustified
   - If it adds > 10%, the iteration is valuable but needs coverage fixes

4. Compare all methods vs greedy on coverage:
   - If greedy achieves comparable coverage at 100x speed, the default should change

**Deliverable:** A data table showing quality/coverage/runtime trade-offs.

**Decision gate:** Proceed to Phase 2 only if the data shows the methods add
value. If genetic is redundant and evolutionary_committee's iteration adds
nothing, proceed directly to Phase 4 (deletion).

### Phase 2: Fix the evolutionary committee's coverage (if Phase 1 shows value)

**Goal:** Add ungrouped fallback to the three graph-bound operators.

**Steps:**

1. **`cold_start_portfolio`** (`evolutionary_operators.py:280-322`):
   - When `graph.neighbors()` returns nothing, fall back to resource-sharing
     candidates from the full pool (similar to `_ungrouped_candidates` in
     `genetic_operators.py:122-158`)
   - This is the highest-impact fix: it makes diversity injection reach the full pool

2. **`add_equipment_to_group`** (`evolutionary_operators.py:33-73`):
   - When `graph.neighbors()` returns nothing, fall back to ungrouped items
     that share resources with the group

3. **`swap_equipment_for_neighbor`** (`evolutionary_operators.py:109-152`):
   - When `graph.neighbors()` returns nothing, fall back to ungrouped items
     that share resources with the group

4. **Add per-expert coverage reporting** to the run manifest:
   - Count items reached by each expert
   - Report coverage delta vs full pool
   - This makes coverage regressions visible

**Files to modify:**
- `processing/evolutionary_operators.py`
- `processing/evolutionary_search_engine.py` (for coverage reporting)
- `main.py` or orchestrator (for manifest reporting)

**Acceptance:** The evolutionary committee reaches >= 99% of the full pool
(currently ~98.2% at ratio 0.15).

### Phase 3: Decide on the genetic expert

**Goal:** Determine whether the genetic expert is a useful refinement or redundant.

**Decision tree:**

```
If Phase 1 shows genetic adds < 5% quality over deterministic:
    -> Deprecate genetic expert (mark as legacy, remove from default paths)
    -> Keep code for reference but remove from CLI --grouping-method options

If Phase 1 shows genetic adds > 10% quality over deterministic:
    -> Keep as a refinement step
    -> Consider: run deterministic first, then genetic only on the graph-reachable set
    -> This gives full coverage (greedy) + refinement (genetic) in one pipeline

If Phase 1 shows genetic is between 5-10%:
    -> Make it opt-in (not default)
    -> Document the trade-off
```

**Files to modify (if deprecating):**
- `main.py` — remove "genetic" from `--grouping-method` choices
- `config_dataclass.py` — mark genetic parameters as legacy
- `REPO_SUMMARY.md` — update method table
- `Makefile` — remove genetic targets

### Phase 4: Clean up and re-default (if warranted)

**Goal:** Simplify the method landscape based on data.

**Possible outcomes:**

**Outcome A — Both methods are valuable:**
- Keep both, but fix coverage (Phase 2)
- Change default to `greedy` (fastest full-coverage) or `hybrid`
- Document when to use each method

**Outcome B — Only evolutionary_committee is valuable:**
- Deprecate genetic expert
- Fix evolutionary committee coverage
- Change default to `greedy` + optional evolutionary refinement

**Outcome C — Neither adds value:**
- Delete both genetic and evolutionary_committee
- Change default to `greedy` (full coverage, fast)
- Keep deterministic for development
- Remove ~1,500 lines of code (genetic_expert, genetic_operators,
  evolutionary_search_engine, evolutionary_operators, evolutionary_fitness,
  evolutionary_search_state, and their tests)

**Outcome D — Evolutionary iteration adds nothing over committee:**
- Delete evolutionary_search_engine + operators + fitness + state
- Keep genetic as a lightweight stochastic search
- Change default to `committee` or `greedy`

---

## 5. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Deleting methods that are actually used | Medium | Phase 1 measurement before any deletion |
| Breaking the committee by removing genetic proposals | Medium | The committee also uses deterministic, random, greedy, baseline proposals |
| Coverage regression from graph threshold changes | Low | Threshold already lowered to 0.15; per-expert reporting added |
| Performance regression from removing evolutionary default | Low | Greedy is 100x faster and full-coverage |

---

## 6. Open Questions

1. **What is the actual quality delta between genetic and deterministic on the
   graph-reachable set?** This determines whether the genetic expert is useful.
   Must be measured in Phase 1.

2. **What is the actual quality delta between evolutionary_committee and
   committee?** This determines whether the evolutionary iteration is justified.
   Must be measured in Phase 1.

3. **Does the greedy expert achieve comparable quality to the evolutionary
   committee?** If yes, the default should change regardless of other decisions.

4. **Are there specific item types or level bands where the genetic/evolutionary
   methods excel?** The data profile shows break density increases with level
   (§8) — maybe stochastic search helps more at high levels.

5. **Is the mutation fallback in genetic_operators sufficient, or does it need
   to be more aggressive?** The current fallback only triggers on empty neighbor
   sets — it may be too narrow.

---

## 7. Files Involved

### Genetic expert (to evaluate)
- `processing/experts/genetic_expert.py` (274 lines)
- `processing/experts/genetic_operators.py` (300 lines)
- `test/test_genetic_expert.py` (if exists)

### Evolutionary committee (to evaluate)
- `processing/evolutionary_search_engine.py` (507 lines)
- `processing/evolutionary_operators.py` (322 lines)
- `processing/evolutionary_fitness.py` (102 lines)
- `processing/evolutionary_search_state.py` (143 lines)
- `test/test_evolutionary_search.py` (330 lines)

### Shared infrastructure (not to be deleted)
- `processing/graph_builder.py` — used by deterministic, genetic, evolutionary
- `processing/group_mapper.py` — used by all experts
- `processing/policy.py` — used by all experts
- `processing/valuation/objective.py` — used by all experts

### Config and entry points
- `processing/config_dataclass.py` — genetic and evolutionary parameters
- `main.py` — CLI method selection
- `analysis_sweep.py` — comparison framework
- `Makefile` — build targets
- `REPO_SUMMARY.md` — documentation

---

## 8. Success Criteria

This plan is successful if:

1. We can make a data-backed decision about whether each method is useful
2. The decision is grounded in measured quality/coverage/runtime, not assumptions
3. If methods are deleted, the remaining pipeline is simpler and faster
4. If methods are kept, their coverage is fixed and their value is documented
5. The default method is the best quality/coverage/speed trade-off

---

## 9. Immediate Next Steps

1. **Run the measurement** (Phase 1) — this is the critical path
2. **Review results** and decide which outcome (A/B/C/D) applies
3. **Execute the chosen outcome** in a follow-up PR
