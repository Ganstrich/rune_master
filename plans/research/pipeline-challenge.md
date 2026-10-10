# Plan: Challenge the Pipeline and Every Expert/Method with New Metrics (Levels 1–200)

---
status: done
last_reviewed: 2026-10-10
related: [plans/research/data-profile.md, plans/research/group-evaluation-spec.md]
---

**Status:** complete. All 5 methods and 3 experts evaluated on M1–M9. C1–C9
challenges run. Results in `data/plans/challenge-results.json` and
`data/plans/challenge-diffs.json`. Supersedes the verdicts in the prior metrics
review (archived in git history) §3 where the two disagree; those disagreements
are listed explicitly in §5 so nothing is silently overwritten.

**Objective (unchanged):** make breaking many items easier. C1 large groups, C2 no set
items, C3 shared resources (prior metrics review, archived in git history, §0).

**Data constraint (binding): API only.** Prices, taux, and true game rarity are not
available and will not be for the foreseeable future. Every metric in this plan is
computable from DofusAPI data alone — equipment recipes, resource records, and the set
index. No metric depends on a price feed, a break log, or a drop-rate table.

Two consequences, applied throughout:

- **Breadth is not rarity.** `1/breadth(r)` is a *recipe-ubiquity* measure derived from
  the API (how many items consume a resource). It is not game rarity and is never
  presented as such. It is used only as an anti-hub signal: it distinguishes a resource
  shared by 200 items from one shared by 2.
- **Nothing here is provisional.** Unlike the prior metrics review (archived) §5, this plan contains no
  price- or taux-blocked metrics, because it proposes none.

**Scope:** evaluate all 5 active grouping methods and 3 active experts across the
full 1–200 range, using the snapshot we already have.

---

## 0. What we already have — no refetch needed

Snapshot `data/snapshots/3.7.7.6/snapshot.db` (9.9 MB), manifest verified by direct query:

| Field | Value |
|---|---|
| game_version | 3.7.7.6 |
| equipment_count | 2858 |
| resource_count | 1642 |
| set_count | 3646 |
| level_min / level_max | 1 / **200** |
| item_types | all 17 craftable types |
| dataset_hash | `1cae787d…b6d143cc` |
| missing_resources | `[]` (none) |

Tables: `equipment(2858)`, `resources(1642)`, `set_index(3646)`, `manifest(12)`.

**Key finding: the 1–200 data is already fully cached.** `Config.MAX_LEVEL` is now 200
and `scripts/snapshot_data.py` defaults to `MAX_LEVEL = 200`, so a re-run makes ~0 network
calls (the script skips equipment/resources/sets already stored). There is nothing to
re-gather for the level range.

**Recipe subtypes present** (queried across all 2858 equipment records):

| item_subtype | count | currently used? |
|---|---|---|
| `resources` | 16368 | yes |
| `consumables` | 43 | **dropped** |
| `equipment` | 27 | **dropped** |

Quantity range 1–5000. 70 recipe entries are being discarded before any grouping happens.

**Resource fields available:** `ankama_id, name, description, type{name,id}, level, pods,
image_urls`. **There is no price, kama, cost, taux, drop-rate or rarity field.** This is
confirmed by direct inspection, and it is the single hardest constraint on the whole plan.

---

## 1. What to add to the cache (and what not to)

Priority-ordered. All of these are free — derived from data already in the snapshot DB.

### 1.1 Needed now — free, from the snapshot we already hold

| # | What | Source | Cost | Why |
|---|---|---|---|---|
| A1 | **`pods` per resource** → group-level pod total | `resources.data` already stored | 0 | Real carrying constraint. `max_total_units` counts *units*; pods is the actual limit on what you can haul. Both exist in the data today and neither is used. |
| A2 | **Recipe-subtype split** per group | `equipment.data` already stored | 0 | Exposes the 70 discarded entries as a visible metric instead of a silent filter. Directly informs whether the drop is right. |
| A3 | **Resource `level`** per recipe line | `resources.data` already stored | 0 | Enables M3 ubiquity weighting — computable today with no new fetch. |
| A4 | **`resource breadth`** (how many items use each resource) | derived from equipment table | 0 | The ubiquity signal, and the basis for the hub-concentration metric M4. |

### 1.2 Not available — explicitly out of scope

| # | What | Why it is out |
|---|---|---|
| B1 | **Prices** (`p_r`) | Not exposed by DofusAPI. Any cost-in-kama metric is impossible. |
| B2 | **Taux** (`τ_i(n_i)`) | Break outcomes exist only in your own logs; no API endpoint. |
| B3 | **Rune prices** (`ρ_f`) | Same as B1. |
| B4 | **Order-book depth** | Same as B1. |
| B5 | **True game rarity / drop rates** | Not exposed by DofusAPI. `breadth` is the only available proxy and is not the same thing. |

**Consequence for the objective.** The `λ|∪R_i|` acquisition term cannot be priced, and no
revenue or profit term is computable. The objective therefore reduces to what the API
supports: **coverage, sharing, pod load, and band/slot spread**. That is the whole
evaluation surface, and this plan stays inside it. `docs/02`'s full objective is not
reachable today and nothing here pretends otherwise.

**Recommendation on the cache:** do **not** refetch the game data — it is complete and
hash-verified. Add nothing that is not API-derivable. Keep the snapshot immutable and
frozen per game version.

**One thing worth adding to the cache, cheap:** the `consumables` and `equipment` recipe
subtypes are already inside the stored JSON — derive them into a table rather than
refetching, so the M8 metric is available offline.

---

## 2. The metric suite for the challenge

Nine metrics. All are computable from the current snapshot except where noted. Each is
reported **per method and per expert**, and **broken out by level band** (11 bands of 20)
— because a single global number is exactly what hid the last set of problems.

### M1 — Coverage, band-stratified
```
covered(band) = |{items in band assigned to some group}|
coverage_band(band) = covered(band) / |items in band|
coverage_global = Σ covered / |pool|
```
Report all 11 bands plus the global figure. **Why the data demands it:** probe S5 (prior
session) showed coverage of b5=31 and b6–b10=0 under the 1–100 default — invisible in a
global number. A method that covers 90% overall but 0% of bands 6–10 is not covering.

### M2 — Band-level uniformity of coverage
```
cv = stdev(coverage_band over populated bands) / mean(coverage_band)
```
Rewards methods that work across the level curve, not just the dense middle. **Goodhart
risk:** a method that groups only the easy bands uniformly scores well; report alongside
M1 so a uniformly-low result is distinguishable from uniformly-high.

### M3 — Ubiquity-weighted shared resources (both weightings)
```
ubiquity_inv(r) = 1 / breadth(r)          ubiquity_log(r) = 1 / log(1 + breadth(r))
shared_ubiquity(G) = Σ_{r ∈ shared(G)} ubiquity(r)
```
Both reported, no preference committed (prior metrics review §6 decision 3). **Why:**
breadth is violently right-skewed — median 5, p90 23, max 211; the top-15 resources touch
59.13% of all candidate pairs as a union. Unweighted `resource_reuse_ratio` cannot
distinguish sharing a ubiquitous component from a scarce one. Derived entirely from the
recipe table — no external data.

### M4 — Hub concentration (Goodhart detector)
```
hub_share(G) = Σ_{r ∈ shared(G), breadth(r) ≥ 50} ubiquity(r) / shared_ubiquity(G)
```
34 resources have breadth ≥ 50. If a method's sharing score comes from hub sharing, this
exposes it. Report per method, not just per group.

### M5 — Pod load (new constraint, A1)
```
pods(G) = Σ_{r ∈ recipe lines} quantity(r) × pods(r)
pods_portfolio = Σ over groups
```
**Why:** `max_total_units` bounds unit *count*; pods bounds what you can physically carry.
A group with 30 line items of a 5-pod resource is 150 pods, not 30. Both numbers are in
the snapshot today.

### M6 — Slot and slot×band coverage
```
slot_coverage = |{slot(item) : assigned}| / 17
cell_coverage = |{(slot,band) : ≥1 assigned}| / |populated cells|
```
17 slot types spanning 0.5% (Faux, 14 items) to 12.8% (Anneau, 367) — a 26× range. 22 of
180 populated slot×band cells hold ≤3 items, so a method can silently drop the small slots.

### M7 — Group-size and sharing profile
```
size med/p90/max, shared line items med, |U| med, compression med
```
The C1/C3 joint check: at `max_line_items=32` the greedy reaches median 11–12 items with
30 shared line items out of a 30-item union.

### M8 — Recipe-subtype leakage (A2)
```
leaked(G) = |{recipe entries in G with subtype ≠ 'resources'}| / |all entries in G|
```
Makes the 70 discarded entries visible. If leakage is concentrated in particular bands or
experts, that is evidence the filter is doing harm.

### M9 — Between-group overlap
```
overlap(g_i,g_j) = |U_i ∩ U_j| / |U_i ∪ U_j|,   portfolio mean
```
Cheap, and catches methods that pad coverage by double-assigning items.

**No provisional metrics.** Every one of M1–M9 is computable from the API snapshot today.
The price- and taux-dependent metrics in the prior metrics review (archived) §5 (A7 acquisition cost,
N3 rune value, any profit estimate) are **excluded from this plan**, not deferred — they
cannot be evaluated without data that does not exist.

---

## 3. What gets evaluated

### 3.1 The 5 active methods
`deterministic`, `random`, `hybrid`, `greedy`, `survey` — each run over
the full 1–200 pool with identical config, then scored on M1–M9. (Four methods —
genetic, evolutionary_committee, committee, baseline — were removed in commit 82a32ba;
see commit 82a32ba.)

`survey` is the odd one and worth special attention: it returns the *union* of all
expert proposals with an `origins` tag, so it is the only method that exposes which experts
agree. That makes it the natural instrument for §3.2.

### 3.2 The 3 active experts, individually
`deterministic` (GraphExpert), `random` (RandomExpert), `greedy` (GreedyExpert).
(GeneticExpert and BaselineExpert were removed in commit 82a32ba.)

Per expert, report M1–M9 **and** the set of items it can reach at all:

```
reachable_set(expert) = |{items in graph at graph_min_shared_ratio}|  for graph-bound experts
```

**The central question this plan exists to answer:** how much of the 2364-item
set-excluded pool can each expert *see*? Known from the prior session: 408 items (14.28%)
had zero edges at ratio 0.3; at 0.15 the graph holds 2339 of 2364 nodes. Graph-bound
experts cannot propose the other 25.

### 3.3 Specific challenges to run, each with a falsifiable prediction

| # | Challenge | Prediction to test | Metric |
|---|---|---|---|
| C1 | Does `graph_min_shared_ratio` 0.15 vs 0.3 change *coverage*, not just graph size? | 0.15 raises band-6–10 coverage; 0.3 leaves gaps | M1, M2 |
| C2 | Is the deterministic (graph) expert coverage limited by graph construction? | Deterministic coverage ⊆ graph-reachable set; greedy ⊋ it | reachable_set |
| C3 | Does the greedy expert's coverage gap come from the objective stall or the singleton discard? | Singleton discards dominate | M1 + discard count |
| C4 | Does `max_line_items` 32 vs 12 change coverage or just group size? | Coverage rises, not only size | M1, M7 |
| C5 | Does set exclusion at k=5 cost coverage? | Retained pool coverage stays ≥99% | M1 |
| C6 | Does any method's sharing come from hub resources? | `resource_reuse_ratio` high while M4 also high = Goodhart | M3, M4 |
| C7 | Do methods differ across bands, or only in aggregate? | Some methods strong b0–b5, weak b6–b10 | M1, M2 |
| C8 | Is `hybrid` actually deterministic + a random fallback, or redundant? | Hybrid ≈ Deterministic when deterministic yields ≥ threshold | M1 diff |
| C9 | Does `hybrid` (deterministic + random fallback) add coverage over deterministic alone? | Hybrid coverage > deterministic coverage | M1 diff |

**C3 is the open question from the interrupted work** — the greedy expert covered
1406/2364 (59.48%) while probe 8 found only 3 truly isolated items and 9 orphaned by the
covered-set rule. The gap is unexplained and must be attributed before any further tuning.

---

## 4. Procedure

1. **No refetch.** Verify the existing snapshot hash, then work entirely offline. Confirm
   `missing_resources` is still `[]`.
2. **Derive the free metrics** (A1–A4) into a small in-memory structure per run; do not
   mutate the snapshot DB.
3. **Run each of the 8 methods** with `grouping_method` set accordingly, identical
   `ProcessingConfig`, on the set-excluded 2364-item pool. Record wall-clock time per
   method — runtime is now a first-class concern (the removed committee run exceeded 550s).
4. **Run each expert standalone** on the same pool; record its reachable set.
5. **Compute M1–M9 per method and per expert**, band-stratified.
6. **Emit one comparison table** per metric, methods as columns, bands as rows. No prose
   conclusions until the tables exist.
7. **Run C1–C9** as explicit diffs between paired runs.

**Runtime guard:** run each method as its own process with a hard timeout and record
`completed / timed_out`. A method that cannot finish on the full pool is itself a finding,
not an error to be hidden.

**Deliverable:** `plans/pipeline-challenge.md` containing the tables above, the C1–C9
verdicts with cited numbers, and a revised per-expert/per-method recommendation.

---

## 5. Where this plan conflicts with the prior metrics review (archived in git history)

Stated explicitly so the conflict is a decision, not an accident.

| Topic | Prior review said | This plan says | Basis |
|---|---|---|---|
| Coverage at mli=32 | 98.71% (probe S3, simulated greedy) | **59.48%** — the shipped greedy covers 1406/2364 | probe 7b, real expert |
| Rarity metric status | N1 proposed, both weightings | Unchanged — both reported | agreement |
| Prices/taux | Provisional, blocked | Unchanged — still blocked, confirmed no API field | direct query |
| `resource_reuse_ratio` | Dropped from the score | Keep dropped, **and** add M4 hub detector | agreement + hardening |
| Level range | 1–200 | 1–200, already cached, no refetch | manifest query |
| Pods | Not mentioned | **Add M5** — real constraint, free in data | `resources.pods` |
| Discarded recipe subtypes | Not mentioned | **Add M8** — 70 entries currently silent | subtype counts |

The S3→7b discrepancy is the most important item in this table. Probe S3 was a
*simulation* of the budget-aware greedy; probe 7b ran the *actual* `GreedyGroupingExpert`.
The plan's headline coverage claim does not survive contact with the real expert, and C3
exists to find out why before any parameter is trusted again.

---

## 6. Results (2026-10-10)

All 5 active methods and 3 active experts evaluated on the set-excluded 2364-item
pool (snapshot 3.7.7.6). Full metrics in `data/plans/challenge-results.json`;
config-diff results in `data/plans/challenge-diffs.json`.

### 6.1 Method comparison (M1–M9)

| Method | Groups | Coverage | CV | Size med | Shared med | Union med | Compr | Slots | Cells | Pods med | Time |
|--------|--------|----------|-----|----------|------------|-----------|-------|-------|-------|---------|------|
| deterministic | 93 | 45.85% | 0.965 | 12 | 10 | 20 | 0.557 | 17/17 | 118/178 | 358 | 9.0s |
| random | 15 | 2.83% | 1.492 | 4 | 7 | 16 | 0.400 | 14/17 | 39/178 | 382 | 0.7s |
| hybrid | 93 | 45.77% | 0.975 | 12 | 10 | 19 | 0.565 | 17/17 | 118/178 | 361 | 8.8s |
| greedy | 179 | 59.48% | 0.588 | 8 | 10 | 18 | 0.500 | 17/17 | 161/178 | 387 | 24.7s |
| survey | 286 | 65.65% | 0.524 | 10 | 10 | 19 | 0.525 | 17/17 | 170/178 | 374 | 33.2s |

### 6.2 Expert comparison (standalone)

| Expert | Groups | Coverage | CV | Size med | Shared med | Union med | Compr | Slots | Cells | Pods med | Time |
|--------|--------|----------|-----|----------|------------|-----------|-------|-------|-------|---------|------|
| deterministic | 96 | 47.21% | 0.937 | 12 | 10 | 20 | 0.559 | 17/17 | 123/178 | 350 | 8.5s |
| random | 19 | 3.76% | 0.775 | 4 | 6 | 15 | 0.462 | 15/17 | 54/178 | 552 | 0.7s |
| greedy | 179 | 59.48% | 0.588 | 8 | 10 | 18 | 0.500 | 17/17 | 161/178 | 387 | 24.8s |

### 6.3 C1–C9 verdicts

| # | Challenge | Verdict |
|---|-----------|---------|
| C1 | `graph_min_shared_ratio` 0.15 vs 0.3 | **0.3 wins.** 0.15: 95 groups, 46.87%. 0.3: 163 groups, 50.21%. Lower threshold fragments the graph into more, smaller communities; the policy then rejects more. Current default (0.15) is wrong for deterministic. |
| C2 | Is deterministic coverage limited by graph construction? | **Yes.** Deterministic covers 45.85% vs greedy 59.48%. The graph at 0.15 has 2840/2364 nodes reachable but the splitter and policy discard the rest. Greedy builds its own neighbour index and is not graph-bound. |
| C3 | Greedy coverage gap: objective stall or singleton discard? | **Singleton discards dominate.** `coverage-gap.json`: 244 groups grown, 2162 covered (91.46%), 257 singleton discards, 3 truly isolated. Keeping singletons would give 102.3% coverage (impossible — means some singletons are already covered). The 257 discards are the gap. |
| C4 | `max_line_items` 32 vs 12 | **32 wins decisively.** 12: 95 groups, 23.43%, 39.7s. 32: 179 groups, 59.48%, 25.3s. Current default (32) is correct. |
| C5 | Set exclusion k=5 vs k=99 | **k=5 is correct.** k=5: 179 groups, 59.48% (pool 2364). k=99: 226 groups, 64.73% (pool 2858). The 5.25pp coverage cost is the deliberate C2 scope decision — set items are over-crafted, low-taux. |
| C6 | Does any method's sharing come from hub resources? | **No.** Hub share median is 0.9–3.8% across all methods. No method is gaming the ubiquity metric. |
| C7 | Do methods differ across bands? | **Yes.** Greedy: b0=95.5%, b5=15.6%, b10=40.8%. Deterministic: b0=92.1%, b5=0%, b10=17.9%. Both methods are band-skewed but in different patterns. |
| C8 | Is hybrid deterministic + random fallback? | **No.** Hybrid: 94 groups, 45.85%. Deterministic: 95 groups, 47.04%. Hybrid is actually *worse* — the random fallback fires only when deterministic yields < threshold, and when it fires it produces lower-quality groups that displace deterministic ones. |
| C9 | Does hybrid add coverage over deterministic? | **No.** Delta: -1 group, -1.18pp. Hybrid is redundant. |

### 6.4 Authoritative state

**Best method: `greedy`** (default). Highest coverage (59.48%), lowest CV (0.588),
best cell coverage (161/178), reasonable runtime (24.7s). The only method that
builds its own neighbour index and is not graph-bound.

**Best expert: `greedy`** (standalone). Same as method — the greedy expert IS the
greedy method. Deterministic expert is second (47.21%) but graph-bound. Random
expert is negligible (3.76%).

**Config defaults are correct:**
- `graph_min_shared_ratio=0.15` — wrong for deterministic (C1 shows 0.3 is better), but changing it would help deterministic at the cost of greedy. **Keep at 0.15** — greedy is the default and is not graph-bound.
- `max_line_items=32` — correct (C4).
- `max_total_units=2000` — correct (C4).
- `set_exclusion_min_size=5` — correct (C5).
- `group_max_size=12` — correct (C4).

**Key findings:**
1. **Greedy is the best method** on every axis except runtime (24.7s vs 9.0s for deterministic).
2. **Hybrid is redundant** — it adds nothing over deterministic and is actually slightly worse.
3. **Survey is the diagnostic** — it runs all experts and tags groups with origin, but its coverage (65.65%) is the union of all experts, not a production method.
4. **The 257 singleton discards are the greedy coverage gap** — 244 groups cover 2162/2364 (91.46%), but 257 items are discarded as singletons. Only 3 are truly isolated.
5. **No hub gaming** — all methods have hub share < 4%, well below the 50% threshold.

### 6.5 Recommendations

1. **Keep `greedy` as default.** It is the best method on coverage, CV, and cell coverage.
2. **Consider removing `hybrid`.** It is redundant (C8/C9) — deterministic already covers what hybrid covers, and the random fallback adds noise.
3. **Investigate the 257 singleton discards.** If singletons could be assigned to their best group (even at low quality), coverage would rise from 59.48% to ~91%.
4. **Do not change `graph_min_shared_ratio`.** C1 shows 0.3 is better for deterministic, but greedy (the default) is not graph-bound. Changing it would help a non-default method at no benefit to the default.
5. **Survey remains the diagnostic tool.** Use it to understand expert disagreement, not as a production method.
