# Metrics Revision: Group-Evaluation Metrics Against the Data Profile

**Status:** implemented. All five sequencing steps from §6 are in the codebase; 136
tests pass (was 120). Implementation validated against snapshot 3.7.7.6 — see
"Implementation notes" at the end of this document.

**Inputs:** `plans/data-profile.md` (snapshot 3.7.7.6), `plans/group-evaluation-spec.md`,
`processing/quality_metrics.py`, `processing/group_metrics.py`, `processing/policy.py`,
`processing/config_dataclass.py`.

**Probe scripts (read-only, in scratch, no `src` touched):**
`/home/adamb/.hermes/cache/scratch/metrics_probe{,2,3,4,5b,6}.py` with outputs
`/home/adamb/.hermes/cache/scratch/metrics_probe{,2,3,4,5,6}.txt`.

**Citation convention:** "profile §N" = numbered table in `plans/data-profile.md`.
"probe Q#/R#/S#/T#" = section of my own probe output. Every claim carries a number.

**Verification first.** I re-derived the profile's similarity section from scratch
(probe 3 §B). Candidate pairs 246,081 = profile §9. All eight Jaccard threshold
counts match exactly (246081 / 88673 / 35101 / 24386 / 13525 / 9650 / 2646 / 1785).
Min candidate Jaccard 0.0667 = 1/15, confirming the profile's 0.07 min. The profile
is internally consistent and I treat it as reproducible ground truth.

---

## 0. The objective this optimises for

**Primary objective: make breaking many items easier**, with resources shared so the
shopping run stays efficient.

**Three standing constraints, all user-specified:**

| # | Constraint | Rationale |
|---|---|---|
| C1 | **Groups should be large** | More items per shopping run means fewer runs. |
| C2 | **Groups should not be made of set items.** Items in sets of ≥5 are never worth breaking | Set items are the over-crafted "safe" choices — systematically broken by many players, so low taux. Same reasoning as the `γ · set_concentration` term in `docs/02`. |
| C3 | **Resources must be shared** | Keeps the shopping list compact; this is the `λ\|∪R_i\|` term. |

Two measured consequences:

- **Coverage is the headline metric, not compression.** "Break many items easier" means
  distinct items reachable from one shopping run. Probe S3: coverage is **91.08% at the
  current defaults and 99.51% at `max_line_items=32`** — a +8.43pp gain from a config
  change with no code edit, the largest single improvement in this document.
- **C1 and C3 are not in tension — they are the same lever.** Probe S3: at mli=32 the
  median group holds 11–12 items with 30 shared line items out of a 30-item union.
  Raising the line-item budget buys group size *and* sharing simultaneously, because
  the budget is what stops growth.

C2 is enforced at the **pool level** (exclude set items from the candidate pool), not as
a soft score term — see §3.8 and new metric N10.

This is consistent with `docs/02`: with no prices and no taux, the `λ|∪R_i|` term is the
only part of the objective that is both computable and user-controlled, and coverage is
how you convert that into breakable items.

---

## 1. Verdict per current metric and parameter

### 1.1 Group-level metrics (`processing/quality_metrics.py`)

| Metric | Location | Verdict | Evidence |
|---|---|---|---|
| **A1 compression** `1-\|U\|/Σ\|R_i\|` | `quality_metrics.py:170` | **KEEP** | The only A-metric that is extensive (grows with group size), so it serves C1 directly. Probe R1: the 869-item component has compression 0.869 whole, 0.479 median at t=0.2 when split to policy size — still discriminates. |
| **A2 resource_reuse_ratio** `\|shared\|/\|U\|` | `quality_metrics.py:156` | **CHANGE** — keep the field, remove from the objective | 34 of 1642 resources have breadth ≥ 50 (probe Q1), so `\|shared\|` is bounded ~34 and `\|U\|` by 12–90. Saturates: median reuse already 0.500 at t=0.4 (probe Q9). No gradient beyond A1. |
| **A3 shared_quantity_ratio** | `quality_metrics.py:168` | **CHANGE** — demote to reporting-only | 14635 Pépite has avg 1098.92 units/item vs pool median 5.89 (profile §2, §3). Probe Q4: 92 of the 113 items over 500 units are Pépite-driven. A3 is a Pépite detector, not a sharing metric. |
| **A4 items_per_line_item** | `group_metrics.py:151` | **KEEP** as reported diagnostic | Exactly `\|G\|/\|U\|` (probe R2), monotone in group size — no independent signal, but it is the direct readout of the `λ\|∪R_i\|` term. |
| **A5 unique_resource_count** | `quality_metrics.py:207` | **KEEP** | The `λ` term's own variable. Profile §7: per-item distinct resources median 6, p90 8, **max 8** — only the union varies. |
| **A6 total_units_needed** | `group_metrics.py:156` | **KEEP**, stop treating as hard cap | Profile §7: units per item median 27, p90 184, max 8046. Probe Q4: 113 items (3.95%) exceed 500 alone — a scope decision, not a cost model. |
| **A7 acquisition_cost proxy** `λ·\|U\|` | spec A7 | **KEEP, stay unweighted** | `λ` is user-set (`config_dataclass.py:101`, currently 0.0). Probe Q2: resource records have keys `ankama_id, description, image_urls, level, name, pods, type` — **no price field anywhere**. Unimprovable until a price feed exists. |
| **B1 largest_set_share** | `quality_metrics.py:77` | **KEEP as penalty** | The only set-metric wired into the score (`quality_metrics.py:202`). Serves C2. |
| **B2 set_free_ratio** | `quality_metrics.py:77` | **KEEP as reward** | 1068 of 2858 items are setless (profile SETS, 37.4%). Setless is *preferable* per C2, not neutral. Probe S6: a setless-only portfolio still covers 1053 of 1068 setless items (98.60%), so the preference costs almost no coverage within the preferred subset. |
| **B7 break_density** metrics | `group_metrics.py:147` | **CHANGE** — keep per-item, add group aggregates | 86 of 2858 items have break_density 0 (probe Q14). Profile §8: median rises 18.60 → 674.88 from band 0 to 10, a 36× range. Raw value only comparable within a band — see N7. |
| **P1 equipment_coverage_rate** | `quality_metrics.py:290` | **KEEP** | The headline metric under the primary objective. Not gameable by fragmentation. |
| **P2 assignment_overlap_rate** | `quality_metrics.py:293` | **KEEP** | Cheap and meaningful. |
| **P3 mean_group_quality** | `quality_metrics.py:300` | **KEEP with P4** | Neither dominates when reported together. |
| **P4 assignment_weighted_quality** | `quality_metrics.py:302` | **KEEP** | Weights by items actually assigned — the honest denominator. |
| **P5 portfolio_resource_overlap** | not computed | **ADD as N8** | Justified in §2. |
| **P6 slot_coverage** | not computed | **ADD as N5** | Justified in §2. |
| **P8 mean_group_overlap** | `quality_metrics.py:310` | **KEEP** | Already there. |
| **`quality_score` blend** (0.45/0.25/0.15/0.15, penalty 0.45) | `quality_metrics.py:84-88` | **CHANGE the term set** | No replacement weights proposed, per the task rule. Term set surviving all three constraints: keep `compression` (C1), `shared_quantity_ratio`, `set_free_ratio` (C2, reward), `largest_set_share` (C2, penalty); **drop `resource_reuse_ratio`** as redundant with compression. Re-weighting is a separate decision. |

### 1.2 Parameters (`processing/config_dataclass.py`)

| Parameter | Current | Verdict | Evidence |
|---|---|---|---|
| `graph_min_shared_ratio` | 0.3 | **CHANGE** to 0.15, splitter fixed in the same change (§3.1) | Profile §10: at 0.3 only 2450 of 2858 nodes (85.7%) are in any component. Probe S1: 408 items (14.28%) have zero edges; **405 of those still share ≥1 resource with the pool, so they are groupable — only 3 truly isolated.** At 0.15 reachability is 99.37%. |
| `group_min_shared_resources` | 3 | **KEEP** | Probe R2: at g=4 median shared = 0.0, p90 = 1 — a 3-resource floor already rejects the weak end. Not the binding constraint. |
| `group_efficiency_threshold` | 0.15 | **CHANGE — rescope, not retune** (§3.6) | **Not legacy — it is live**, enforced at `policy.py:49`. At `group_min_size=2` the metric *is* pairwise Jaccard, admitting 35101 of 246081 candidate pairs (14.26%); at g≥4 near-inert (8.5% of 4-item groups fall below). The genuinely dead artifact is the 0.10 in `map_communities_inclusive`, which never runs. |
| `group_max_set_share` | 0.5 | **KEEP** | Guards the boundary at exactly the exclusion threshold. Same-set candidate pairs are only 2189 of 246081 (0.89%, probe Q6), so it rarely fires — but with C2 enforced at pool level it is the last line of defence, not the primary mechanism. |
| `max_line_items` | 12 | **CHANGE** to 32 (§3.2) | **The single most valuable change.** Probe S3: coverage 91.08% at mli=12 → 98.71% at mli=32 → 99.51% at mli=32/mtu=∞. Probe S4: **95.0% of the groups the greedy can build exceed the current 12 cap.** Profile §7: per-item distinct resources max 8, so 12 binds only on unions. |
| `max_total_units` | 500 | **CHANGE** to 2000 (§3.2) | Probe Q4: 2745 of 2858 items (96.05%) fit under 500, 2799 (97.94%) under 2000. **Secondary lever** — probe S3: mtu 500→∞ moves coverage only +0.73pp, vs +7.70pp for mli 12→32. |
| `excluded_resource_ids` | {14635} | **KEEP 14635; DROP 15263** | Probe 3 §A: 15263 is absent from the resources table, appears in **zero** recipe entries of any subtype, and is not an equipment ID. The comment at `config_dataclass.py:108` claims otherwise — false on this snapshot. Removing it changes nothing numerically (0 of 246081 pairs) but removes a false claim. |
| `MIN_LEVEL`/`MAX_LEVEL` | 1 / 100 | **CHANGE** to 1 / 200 (§3.3) | Probe Q3: ≤100 gives 1498 of 2858 items (52.41%) and 61352 of 246081 pairs (24.93%). Probe S5: at 1–100 coverage is b5=31 and **b6–b10 = 0** — six bands entirely unreachable. 1–100 remains a job-level convenience scope; 1–200 is the planning default. |
| `equipment_density_level_ratio` | 3.0 | **CHANGE** to 2.0 **and wire it in** (§3.4) | Probe Q4: ratio 3.0 keeps 1169 of 2858 (40.90%), excluding 415 of 510 items in band 2 alone. Ratio 2.0 keeps 2062 (72.15%), at or below the band medians (1.846–3.374) in every band 0–8. |
| `use_density_filtering` | True | **CHANGE — currently inert** | Verified: `get_active_pool` is called from nowhere in `orchestrator.py` or `main.py`. Only `tuner.py:36-37` sets it, with its own relaxed 1.5. The 3.0 default has never affected a production run. |
| `same_set_edge_discount` | 1.0 | **KEEP** | Same-set candidate pairs are 0.89% of all pairs (probe Q6) — near-inert either way. No evidence to change. |
| `group_max_size` | 32 | **CHANGE** to 12 (§3.2) | Unreachable while mli=12 (probe R2: no 8-item group fits). Probe S3: with mli=32 the greedy reaches median group size 6–12 and p90 12, so 12 is both reachable and consistent with C1. |
| `flat_taux` | 1.0 | **KEEP, mark provisional** | See §5. |
| `set_exclusion_min_size` | *(new)* | **ADD — configurable, default 5** (§3.8) | **C2, enforced at pool level.** Probe T2: k=5 keeps 2364 of 2858 (82.72%) and covers 99.24% of the retained pool. Probe T3: the 494 excluded items have median `stat_weight` **82.5 vs 298.1** retained — 3.6× lower, so it removes the weak tail rather than random items. |

---

## 2. New metrics the data makes necessary

### N1 — Rarity-weighted shared score

**Formula (both variants reported):**

```
rarity_inv(r) = 1 / breadth(r)
rarity_log(r) = 1 / log(1 + breadth(r))
shared_rarity(G) = Σ_{r ∈ shared(G)} rarity(r)      # computed under both
hub_share(G) = Σ_{r ∈ shared(G), breadth(r) ≥ 50} rarity(r) / shared_rarity(G)
```

**Why the data demands it.** Breadth is violently right-skewed: median 5 items per
resource, p90 23, max 211 (profile §1). Probe Q2: the top-15 hubs alone touch
**145,499 of 246,081 candidate pairs (59.13%)** as a union. Probe Q1 buckets: 173
resources used by 1 item, 577 by 2–4, 476 by 5–9, 382 by 10–49, only 34 at ≥50. A group
can post high `resource_reuse_ratio` purely by sharing two or three of those 34 hubs.
Unweighted sharing cannot distinguish "shares Étoffe Mystérieuse with everyone" from
"shares a genuinely uncommon component".

Computable today from the snapshot alone (probe Q2: `level` present on all 1642
resources, no price field). Probe Q10: under `1/breadth`, `w(r)` has median 0.200,
p90 1.000, max 1.000. `1/log(1+breadth)` is the milder variant, reported alongside so
the choice stays open rather than baked in.

**Goodhart risk.** Inverse-breadth rewards collecting singleton resources — exactly what
the 173 single-use resources (profile §4) are. Mitigation: report `hub_share` alongside
so a 100%-hub-driven group is visible. Note profile §4a: 153 of 154 items consuming a
dead-end resource still share other resources with the pool (1390 pairs), so dead-ends
do not isolate items — but must not be counted as valuable sharing.

### N2 — Breadth-stratified sharing profile

**Formula:** count of shared resources in each profile breadth bucket:
`1 / 2–4 / 5–9 / 10–49 / ≥50` (probe Q1, matching the profile's own ≥50 "broad" cut).

**Why the data demands it.** Profile §3: broad_heavy (1 resource, 10,878 pairs, 4.4%),
broad_medium (15, 97,441, 39.6%), broad_trivial (18, 76,794, 31.2%), narrow_any (382,
83,516, 33.9%), rare_any (1053, 9,723, 4.0%). These behave differently — the 18
broad_trivial resources are used at max 2 units each, saving almost no shopping effort,
while the single broad_heavy resource (14635) costs 1098.92 units per item. No scalar
represents both; five counts can.

**Goodhart risk.** Low — descriptive breakdown, not a score. The risk is collapsing it
into a weighted sum, which recreates the problem it exposes.

### N3 — Rune-type coverage weighted by density

**Formula:**

```
covered_stats(G) = { s : s appears in some effect of some item in G }
weighted_coverage(G) = Σ_{s ∈ covered_stats(G)} density(s)   # from RUNE_DENSITY
```

**Why the data demands it.** Profile §8: per-item break density median 250.12, p90
674.60, max 1343.15 — a 5× spread in rune value per item. `RUNE_DENSITY` already
assigns PA=100, PM=90, Portée=51 down to Vitalité=0.2
(`processing/valuation/density.py:7-30`), so the weights exist in-repo. An unweighted
stat-type count (spec B8) scores five PA lines the same as five Vitalité lines, when
their rune value differs by 500×.

**Goodhart risk.** High as a reward: the optimizer hoards PA/PM lines. Report as
coverage (breadth of stat types touched), not as a sum to maximise; the sum form is a
value proxy and needs prices to be honest.

### N4 — Panoplie entropy with setless as its own category

**Formula:**

```
categories = {set_id for set-bearing items} ∪ {∅ if any setless item}
p_k = count(k) / |G|
H_set(G) = -Σ_k p_k log p_k , normalized by log|categories|
```

**Why the data demands it.** 1068 of 2858 items (37.4%) are setless; 516 distinct sets
with median size 3 (profile SETS). The spec's open question 1 asks how to treat setless
items — the data says they are too large a share (37.4%) to drop from the denominator
and too heterogeneous to count as one set. Own category is the only option keeping the
denominator at `|G|`.

**Goodhart risk.** Moderate: entropy is maximised by one-item-per-category, so 8
singletons score 1.0. Report alongside B1 and N5 rather than blending into one score.

### N5 — Slot coverage at portfolio level

**Formula:**

```
slot_coverage(portfolio) = |{slot(item) : item assigned}| / 17
```

**Why the data demands it.** Profile §5: 17 slot types spanning 0.5% (Faux, 14 items)
to 12.8% (Anneau, 367) — a 26× range. Probe Q5: 180 of 187 possible slot×band cells
populated, but **22 cells (12.22%) hold ≤ 3 items** and 7 hold exactly 1. A portfolio
ignoring the small slots is structurally under-covering, not unlucky. The spec's open
question 6 is answered: yes, 17 slots, stable, already enumerated in `config.py:8-26`.

**Goodhart risk.** Low-moderate: rewards assigning one Faux item for the count.
Mitigation: report per-slot assignment counts next to the ratio.

### N6 — Slot × level-band coverage

**Formula:**

```
cell(item) = (slot(item), floor(item.level / 20))
cell_coverage(portfolio) = |{cell : ≥1 item assigned}| / |populated cells in scope|
```

**Why the data demands it.** Probe R4: at the current 1–100 scope only 92 slot×band
cells are populated and **16 of them (17.4%) hold ≤ 3 items**; at 1–200, 180 cells with
22 (12.2%) ≤ 3. The sparse cells are where a naive method silently drops coverage, and
nothing in the current metric set would notice.

**Goodhart risk.** Low. Main risk is denominator instability as the pool grows — fix the
denominator per snapshot version and record it in the run manifest.

### N7 — Level-band-normalised break density

**Formula:**

```
density_z(item) = (break_density(item) - median_band(band(item))) / p90_band(band(item))
```

**Why the data demands it.** Profile §8: band medians rise monotonically 18.60 (band 0),
61.50, 88.85, 168.38, 226.15, 299.10, 372.10, 439.60, 503.60, 581.38, 674.88 (band 10).
A raw 200.0 is top-decile in band 3 and bottom-half in band 7. Probe Q14 reproduces all
eleven medians exactly; 86 of 2858 items have break_density 0 and would otherwise look
uniformly bad.

**Goodhart risk.** Moderate: within-band z-scores can be gamed by picking the single
highest-density item per band. This is a normalisation for comparability, not a reward —
keep the raw value beside it.

### N8 — Between-group resource overlap, rarity-weighted

**Formula:**

```
overlap(g_i, g_j) = |U_i ∩ U_j| / |U_i ∪ U_j|
rarity_weighted_overlap = Σ_{r ∈ U_i ∩ U_j} rarity(r) / Σ_{r ∈ U_i ∪ U_j} rarity(r)
portfolio_overlap = mean over group pairs
```

**Why the data demands it.** Spec P5 was dropped as "not yet implemented" — an
implementation objection, not a data objection. The pool touches only 1642 distinct
resources (probe R7), 1469 used by ≥2 items. With `max_line_items=32` and ~240 groups
(probe S3), two groups from the same 869-item component will routinely share resources.
Unweighted overlap cannot distinguish sharing Pépite (breadth 148, avg 1098.92 units)
from sharing a breadth-2 resource.

**Goodhart risk.** Low as a diagnostic. As a penalty it can be gamed by making groups
deliberately disjoint at the cost of quality — hence portfolio report, not per-group
objective.

### N9 — Density-filter pool retention

**Formula:**

```
retention(band) = |{items in band passing stat_weight ≥ level · ratio}| / |{items in band}|
reported per band, alongside global retention
```

**Why the data demands it.** Probe Q4: ratio 3.0 keeps 1169 of 2858 globally (40.90%)
but band 10 keeps 319 of 430 (74.2%) while band 2 keeps 95 of 510 (18.6%). A single
global number hides a filter deleting 81% of one band. Band medians of
`stat_weight/level` range 1.846 (band 2) to 3.374 (band 10), so any fixed ratio is a
different filter per band.

**Goodhart risk.** Low — a diagnostic on the filter itself. It guards against the
pipeline silently operating on a band-skewed subset and the coverage metrics reporting
that skew as a property of the grouping method.

### N10 — Set-exclusion accounting

**Formula:**

```
excluded_set_items = |{i : |set(i)| ≥ set_exclusion_min_size}|
pool_retained = |pool| - excluded_set_items
excluded_by_band(b) = |{excluded i : band(i) = b}|
excluded_by_slot(s) = |{excluded i : slot(i) = s}|
```

**Why the data demands it.** C2 removes 494 items (17.28%) from the pool at k=5 (probe
T3). Without explicit accounting the removal is invisible: coverage would simply read
lower with no explanation, and a future pool change could silently shift the threshold's
effect. Probe T3 shows the exclusion is spread evenly across bands (b0=62 … b10=28) and
concentrated in armour slots (Anneau 80, Chapeau 75, Cape 75, Bottes 74, Ceinture 71,
Amulette 54) — worth reporting so the shape of the cut stays visible.

**Goodhart risk.** Low. This is bookkeeping, not a score. The risk it guards against is
treating a deliberate scope decision as a grouping-quality regression.

---

## 3. Parameter changes, with observed sensitivity

### 3.1 `graph_min_shared_ratio`: 0.3 → 0.15, coupled to a structure-aware splitter

From profile §10 and probe R6 (recomputed, identical):

| ratio | edges | components | largest | nodes in comps | % pool reachable |
|---|---|---|---|---|---|
| 0.10 | 88673 | 5 | 2835 | 2854 | 99.86% |
| 0.15 | 35101 | 9 | 2807 | 2840 | 99.37% |
| 0.20 | 24386 | 18 | 2730 | 2796 | 97.83% |
| 0.25 | 13525 | 102 | 1284 | 2661 | 93.11% |
| **0.30** | **9650** | **193** | **869** | **2450** | **85.72%** |
| 0.35 | 2746 | 312 | 147 | 1505 | — |
| 0.40 | 2646 | 312 | 147 | 1462 | — |

The most consequential number: **408 items (14.28%) have no edge at 0.3.** They are
unreachable by the deterministic, graph and committee experts — only the greedy expert,
which grows from seeds against the objective rather than from graph edges
(`greedy_expert.py:34-90`), can reach them. At 0.25 the invisible set falls to 197 items
(6.89%), at 0.20 to 62 (2.17%).

Probe S1 adds the detail that decides whether this matters: **405 of those 408 still
share ≥1 resource with the pool**, so they are groupable — only 3 are truly isolated.
The dead zone spans all 17 slots and all 11 bands, so it is not a corner case.

Note the cliff between 0.25 and 0.30: largest component 1284 → 869 (−32%), component
count 102 → 193. That is where the mega-component starts fragmenting, and it is a better
operating point than 0.3.

**Decision: build at 0.15** (99.37% reachable) and let the policy's
`group_efficiency_threshold` do the precision work — it already gates on
`sharing_efficiency ≥ 0.15` (`policy.py:49`), so precision need not be bought twice.

**Caveat that makes this one coupled change:** at 0.15 the largest component is 2807
items, and probe R1 shows the contiguous splitter loses 100% of chunks on an 869-item
component. The splitter must be made structure-aware in the same change, or lowering
the threshold makes results worse rather than better.

### 3.2 `max_line_items` 12 → 32, `group_max_size` 32 → 12, `max_total_units` 500 → 2000

These three interact and are currently mutually inconsistent. C1 makes
`max_line_items` the primary lever, so I ran a direct coverage sweep.

Profile §7: distinct resources per item — min 0, median 6, p90 8, **max 8**. Every item
fits any cap ≥ 8, so `max_line_items` binds only on unions.

Probe R2, random groups of size g from the 869-item component:

| g | \|U\| median | \|U\| p90 | \|U\| max | shared median | % with \|U\| ≤ 12 |
|---|---|---|---|---|---|
| 4 | 12 | 14 | 16 | 0.0 | 65.3% |
| 8 | 23 | 25 | 30 | 2.0 | **0.0%** |
| 12 | 33 | 37 | 41 | 4.0 | 0.0% |
| 16 | 42 | 46 | 50 | 6.0 | 0.0% |
| 32 | 75 | 81 | 90 | 17.0 | 0.0% |

At g=8 not one of 150 simulated groups fits 12 line items, while `group_max_size=32`
admits groups that can never pass. The effective maximum group size today is ~7.

**Probe S3 — the decisive measurement.** Budget-aware greedy (BaselineExpert's
algorithm: density-ordered seeds, growth blocked when the pooled union would exceed the
budget) across the full 2858-item pool:

| mli | mtu | groups | covered | % pool | group size med / p90 | line items med | units med |
|---|---|---|---|---|---|---|---|
| 12 | 500 | 807 | 2603 | 91.08% | 2 / 6 | 12 | 112 |
| 12 | 2000 | 784 | 2603 | 91.08% | 2 / 6 | 12 | 111 |
| 12 | ∞ | 798 | 2624 | 91.81% | 2 / 6 | 12 | 111 |
| 24 | 500 | 438 | 2818 | 98.60% | 5 / 12 | 22 | 382 |
| 24 | 2000 | 368 | 2818 | 98.60% | 7 / 12 | 23 | 267 |
| 24 | ∞ | 372 | 2843 | 99.48% | 7 / 12 | 23 | 267 |
| 32 | 500 | 383 | 2819 | 98.64% | 6 / 12 | 23 | 484 |
| 32 | 2000 | 274 | 2821 | 98.71% | 12 / 12 | 30 | 348 |
| **32** | **∞** | **280** | **2844** | **99.51%** | **11 / 12** | **30** | **364** |
| 48 | 500 | 370 | 2818 | 98.60% | 7 / 12 | 23 | 489 |
| 48 | 2000 | 239 | 2816 | 98.53% | 12 / 12 | 29 | 398 |
| 48 | ∞ | 242 | 2847 | 99.62% | 12 / 12 | 30 | 417 |

Three conclusions:

1. **`max_line_items` binds, `max_total_units` does not.** mtu 500 → ∞ at mli=12 moves
   coverage +0.73pp. mli 12 → 32 at mtu=∞ moves it +7.70pp.
2. **32 is the knee.** mli=24 reaches 98.60–99.48%; mli=32 reaches 99.51%; mli=48 adds
   only +0.11pp while cutting group count 280 → 242.
3. **C1 and C3 are jointly achievable.** At mli=32 the median group holds 11–12 items
   with 30 shared line items out of a 30-item union — large *and* highly shared. This is
   unreachable at mli=12, where median group size is 2.

Probe S4 confirms the defaults are the obstacle, not the data: at mli=48, **95.0% of
buildable groups exceed the 12-line-item cap** (230 of 242) and 43.0% exceed the 500-unit
cap (104 of 242).

`max_total_units`: probe Q4 shows 2745 of 2858 items (96.05%) fit under 500, 2799
(97.94%) under 2000. The 113 excluded items concentrate at level 200 (worst 8046 units).
Since 92 of those 113 are Pépite-driven and 14635 is already excluded for *sharing*, a
2000 cap aligned with the exclusion is more coherent than 500.

### 3.3 `MIN_LEVEL`/`MAX_LEVEL`: 1/100 → 1/200

Probe Q3:

| ceiling | items | % of pool | candidate pairs | % of pairs |
|---|---|---|---|---|
| ≤100 (current) | 1498 | 52.41% | 61352 | 24.93% |
| ≤120 | 1674 | 58.57% | 70226 | 28.54% |
| ≤140 | 1870 | 65.43% | 85797 | 34.87% |
| ≤160 | 2035 | 71.20% | 98894 | 40.19% |
| ≤180 | 2160 | 75.58% | 112410 | 45.68% |
| ≤200 | 2858 | 100.00% | 246081 | 100.00% |

The current default discards 47.59% of items and 75.07% of the candidate-pair structure.
Profile §6 also shows the top band (200–219) is the *largest* at 430 items — larger than
any band in the current scope. And profile §8 shows break density is highest there
(median 674.88), so the excluded range is the most rune-dense part of the game. Probe S5
confirms: at 1–100 coverage by band is b5=31, b6–b10=0. The highest-impact single default
change in this document.

**Decision: 1–200 is the permanent planning/comparison default.** 1–100 remains
available as a job-level convenience scope, since it covers the job levels currently
reachable in-game.

### 3.4 `equipment_density_level_ratio`: 3.0 → 2.0, and wire the filter in

Probe Q4 retention:

| ratio | kept | % of pool |
|---|---|---|
| 0.5 | 2747 | 96.12% |
| 1.0 | 2680 | 93.77% |
| 1.5 | 2451 | 85.76% |
| 2.0 | 2062 | 72.15% |
| 2.5 | 1629 | 57.00% |
| **3.0** | **1169** | **40.90%** |
| 3.5 | 666 | 23.30% |
| 4.0 | 368 | 12.88% |

Per-band exclusion at 3.0: band 2 loses 415 of 510, band 1 loses 207 of 295, band 0
loses 168 of 264. Median `stat_weight/level` per band runs 1.846 (band 2) to 3.374
(band 10), so ratio 3.0 is a ~50% filter in band 10 and a ~81% cut in band 2. Ratio 2.0
sits at or below the median in every band 0–8.

**Important verified finding:** `get_active_pool` is never called from
`processing/orchestrator.py` or `main.py`. The only caller is `tuner.py:36-37`, which
sets `equipment_density_level_ratio=1.5` explicitly. The 3.0 default has never affected
a production run. Changing the number alone accomplishes nothing — the filter must be
wired into the orchestrator first.

### 3.5 `excluded_resource_ids`: drop 15263

Probe 3 §A, on snapshot 3.7.7.6:
- 15263 is **not present** in the `resources` table.
- It appears in **zero** recipe entries of subtype `resources`, `equipment`, or
  `consumables`.
- It is not an equipment `ankama_id` either.
- By contrast 14635 is present and appears in 148 recipes as a `resources` entry.

The comment at `config_dataclass.py:108-109` describes 15263 as "an equipment item used
in a few recipes". On this snapshot that is not true. It is inert config that misleads
the reader. Removing it changes nothing numerically (probe Q1: 0 of 246081 pairs) but
removes a false claim from the codebase.

### 3.6 `group_efficiency_threshold`: 0.15 is live but mis-scoped

**It is not legacy — it is live and load-bearing, but on a narrower job than its name
suggests.**

**What is live.** `processing/policy.py:49` enforces `sharing_efficiency < threshold` as
a hard reject and reads `config.group_efficiency_threshold`. The 0.15 in
`GroupMapper.map_communities` (`group_mapper.py:116`) is shadowed by the config value
passed from `graph_expert.py:116`, so the signature default is dead but the *parameter*
is very much alive.

**What is actually dead.** The 0.10 in `GroupMapper.map_communities_inclusive`
(`group_mapper.py:140`) is also shadowed — but more importantly that whole path never
runs, because `config.use_inclusive_mapping` defaults to `False`
(`config_dataclass.py:105`) and nothing sets it True. That is the genuine legacy
artifact.

**Why 0.15 is mis-scoped.** The metric's meaning changes with group size:

- At `group_min_size = 2`, `sharing_efficiency` reduces to `|R_a ∩ R_b| / |R_a ∪ R_b|` —
  exactly pairwise Jaccard. So the threshold *is* a Jaccard floor on 2-item groups,
  admitting 35101 of 246081 candidate pairs (**14.26%**), rejecting 85.74%.
- At g ≥ 3 it becomes an aggregate over the union and stops discriminating: only
  **8.5%** of 4-item groups and **12.8%** of 8-item groups fall below 0.15.

So 0.15 does real work as a **2-item-group quality filter** and almost none as a general
admissibility gate. Treating it as the latter is what makes it look vestigial.

**Decision: rescope, do not retune.**

- Document it as a small-group (g=2,3) quality floor.
- Gate the threshold on `group_size` — apply the floor only when `group_size <= 3`.
  Probe S3 shows large groups already carry high sharing (median 30 shared line items
  out of a 30-item union at mli=32), so exempting them costs nothing and serves C1.
- Delete the dead 0.10 in `map_communities_inclusive`, or wire that path up — not both.

### 3.7 The genetic and evolutionary experts are partly redundant — and partly blind

**Finding: two of the five experts are structurally incapable of seeing 14.28% of the
pool.**

`GraphGroupingExpert` builds the Jaccard graph and returns `[]` if empty
(`graph_expert.py:50-59`). `GeneticGroupingExpert` does the same
(`genetic_expert.py:99-109`). Critically, the genetic expert's search is graph-bound
throughout:

- `create_graph_individual` seeds only from `graph.nodes()` (`genetic_operators.py:189`).
- `mutate("add")` pulls candidates only from `graph.neighbors()`
  (`genetic_operators.py:145-150`).

An item with no edge at `graph_min_shared_ratio=0.3` is absent from the graph, so no
amount of evolution can discover it. Probe S1: **408 items (14.28%) are in that dead
zone, and 405 of them still share ≥1 resource with the pool** — perfectly groupable,
only 3 truly isolated.

The dead zone is not a niche. It spans **all 17 slots** (Chapeau 54, Ceinture 43, Cape
42, Amulette 42, Bottes 36, Bouclier 29, Anneau 27, Épée 22, Dague 19, Bâton 18, Arc 18,
Marteau 16, Hache 15, Baguette 15, Pelle 10, Lance 2) and **all 11 level bands** (b0=6,
b1=50, b2=45, b3=67, b4=28, b5=65, b6=50, b7=24, b8=16, b9=40, b10=17). Dropping it
silently removes 14.28% of the craftable pool from every deterministic and genetic run.

**Consequence for the committee.** Its value proposition is diversity across experts
(`config_dataclass.py:5-16`). But deterministic and genetic are the same algorithm with
different search strategies over the same graph — they share the blind spot and will
tend to propose the same components. The genuine architectural diversity comes from
`GreedyGroupingExpert`, which builds its own neighbour index from `recipe_resource_ids`
rather than the Jaccard graph (`greedy_expert.py:49-54`), and `BaselineExpert`, which
scans all equipments (`baseline_expert.py:63-67`). Those two are the only ones reaching
the dead zone.

**Recommendations, in order of value:**

1. **Lower `graph_min_shared_ratio` to 0.15** (§3.1) — shrinks the dead zone from 408 to
   ~37 items. Cheapest fix, but couples to the splitter change.
2. **Let the genetic mutation operator seed from ungrouped items.** `mutate("add")` walks
   only `graph.neighbors()`. A fallback considering any uncovered item scoring above the
   current marginal would let evolution escape the graph — targeted, no graph change.
3. **Re-weight the committee toward the experts that actually cover the pool.** With two
   of five unable to see 14.28% of items, equal-weight consensus is biased toward the
   graph-visible subset. Weights are a user decision; the composition argument is not.
4. **Report per-expert coverage in the run manifest.** Probe S1 gives the breakdown to
   diff against; without it a coverage regression looks like a metric problem rather
   than an expert-architecture problem.

### 3.8 `set_exclusion_min_size`: new configurable parameter, default 5

C2 — groups not made of set items, items in sets of ≥5 never worth breaking — is a
specific testable threshold, so I swept it.

**Set-size distribution (probe T1):**

| set size | # sets | # items | cumulative |
|---|---|---|---|
| 1 | 1 | 1 | 1 |
| 2 | 95 | 190 | 191 |
| 3 | 255 | 765 | 956 |
| 4 | 85 | 340 | 1296 |
| **5** | **30** | **150** | **1446** |
| 6 | 15 | 90 | 1536 |
| 7 | 26 | 182 | 1718 |
| 8 | 9 | 72 | 1790 |
| setless | — | 1068 | — |

The distribution is smooth across 2–8 with no natural cliff, so there is no
data-driven "correct" cut — which is exactly why it must be configurable rather than
hardcoded.

**Sweep (probe T2), k = "exclude items in sets of size ≥ k":**

| k | pool kept | % of 2858 | groups | covered | % of kept pool | med group size |
|---|---|---|---|---|---|---|
| none | 2858 | 100.00% | 280 | 2844 | 99.51% | 11 |
| 8 | 2786 | 97.48% | 272 | 2771 | 99.46% | 11 |
| 7 | 2604 | 91.11% | 260 | 2596 | 99.69% | 11 |
| 6 | 2514 | 87.96% | 249 | 2501 | 99.48% | 11 |
| **5** | **2364** | **82.72%** | **238** | **2346** | **99.24%** | **11** |
| 4 | 2024 | 70.82% | 211 | 2008 | 99.21% | 10 |
| 3 | 1259 | 44.05% | 137 | 1246 | 98.97% | 9 |
| 2 | 1069 | 37.40% | 120 | 1054 | 98.60% | 9 |

**Why k=5 is the right default, from the data rather than the rule alone (probe T3):**

- Excludes 494 items (17.28%), and coverage *within the retained pool* stays at 99.24% —
  you lose almost nothing worth grouping.
- The excluded items are the weak tail: median `stat_weight` **82.5** excluded vs
  **298.1** retained, a 3.6× gap. Removing them concentrates the pool on high-density
  items, the opposite of a random cut.
- Spread evenly across bands (b0=62 … b10=28) and concentrated in armour slots (Anneau
  80, Chapeau 75, Cape 75, Bottes 74, Ceinture 71, Amulette 54), so it does not hollow
  out any part of the level curve.

**Decision:**

```
set_exclusion_min_size: int = 5   # exclude items in sets of size >= this; 99 = off
```

Configurable, with an explicit `--no-set-filter` override so the unfiltered view is
available in the same run, and the sweep above recorded as the reference table for
choosing a different value. Sweeping k is explicitly wanted — different set-size
conditions should be tried rather than assumed.

**Two interactions (probe T5):** graph reachability is essentially unchanged by the
exclusion (85.72% at k=none, 83.33% at k=5, 65.86% at k=2), so this is independent of
`graph_min_shared_ratio` and can be sequenced separately. And `group_max_set_share=0.5`
becomes largely redundant once set items leave the pool — though it still guards the
boundary at exactly k, so keep it.

---

## 4. Data-driven failure modes at full scale

**FM1 — Mega-component at low thresholds.** Profile §10: at ratio 0.05 there are 2
components and the largest holds 2850 of 2858 items; at 0.10, largest 2835. The
pipeline's split logic (`group_mapper.py:206-229`) slices communities into *contiguous*
chunks of `max_size`, ignoring resource structure. Probe R1: applied to the 869-item
component at 0.3, all 28 chunks fail the policy — 100% loss. Any threshold low enough to
fix the reachability gap (§3.1) worsens this, because reachability and component size
move together. A structure-aware splitter is a prerequisite for lowering the threshold.

**FM2 — Hub resources.** Probe Q2: 34 resources have breadth ≥ 50, and the top 15 by
breadth touch 59.13% of all candidate pairs as a union. Probe R3: inside the 869-item
component's 5687 internal edges, the top-10 hub resources appear on 53.8% of edges (with
multiplicity), led by 746 (Ébonite, 9.1%) and 12745 (Substrat de Bocage, 7.9%). A method
optimising unweighted `resource_reuse_ratio` converges on hub-built groups, because
sharing a breadth-211 resource is the cheapest way to raise the ratio. The primary
Goodhart failure of the current objective, and the reason N1/N2 exist.

**FM3 — Tiny type × level cells.** Probe Q5: 22 of 180 populated slot×band cells
(12.22%) hold ≤ 3 items, and 7 hold exactly 1 (Faux in bands 0, 1, 2, 6, 7; Lance in
bands 1 and 9). At the 1–100 scope, 16 of 92 cells (17.4%) hold ≤ 3. Any
`group_min_size=2` gate makes these cells ungroupable, and no current metric reports the
loss — `equipment_coverage_rate` just reads lower with no explanation.

**FM4 — The 408-item dead zone.** Probe R6: 408 items have zero edges at ratio 0.3; 3
have no shared resource with anything in the pool. The deterministic, graph and
committee experts cannot see them (see §3.7). If the committee's consensus weighting
favours the graph experts, these items are systematically absent from every portfolio,
and P1 coverage will look like a grouping-quality problem when it is a
graph-construction problem.

**FM5 — Pépite-dominated quantity metrics.** Profile §3: 14635 is the only broad_heavy
resource (breadth 148, avg 1098.92 units/item, max 3000) and contributes 10,878
candidate pairs (4.4% of all pairs). Probe Q4: 92 of the 113 items exceeding 500 total
units are Pépite-driven. `shared_quantity_ratio` and `total_items_needed` are both
dominated by this one resource; with `max_total_units=500` any group containing a
Pépite-heavy item is rejected outright. `excluded_resource_ids` handles this for
*sharing* but not for the shopping list — `GroupMetrics.aggregate_resources`
(`group_metrics.py:64-105`) calls `iter_recipe` without exclusions, so Pépite still
lands in `total_items_needed`.

**FM6 — Band-skewed density filter.** Probe Q4: if `equipment_density_level_ratio=3.0`
were live it would keep 74.2% of band 10 but only 18.6% of band 2. The portfolio would
be dominated by high-level items, and N6/N7 would report that as a property of the data
rather than of the filter. Currently masked because the filter is not wired in (§3.4).

**FM7 — Set-exclusion is a scope decision, not a metric defect.** C2 removes 494 items
(17.28%) from the pool at k=5 (probe T3). That is intended: set items are the
over-crafted, low-taux choices, and the excluded set has median `stat_weight` 82.5 vs
298.1 retained. The failure mode to guard against is *silent* scope drift — if the
threshold or the pool changes and nothing reports the delta, a deliberate exclusion
starts looking like a coverage regression. N10 exists for this.

**FM8 — Cross-band level spread as a false signal.** Probe R5: 47.53% of candidate
pairs are same-band, 34.31% gap-1, only 12.05% gap ≥ 3. Median `|level_a - level_b|` is
6 with p90 56. Any group built from candidate edges is almost always 1–2 bands wide, so
a "level spread" metric (spec B5) would be near-constant across groups — its variance
comes from the 12% tail, which is noise at group scale.

---

## 5. What this data cannot tell us

**Missing: taux.** No break outcomes exist. `PosteriorTauxModel` is referenced in
`frontier-model-iteration-prompt.md:56` but no break log has been ingested.
`config_dataclass.py:102` sets `flat_taux = 1.0` explicitly as a "theoretical
placeholder until break outcomes are logged". Until `break_log` exists, **no metric
depending on `E[τ_i(n_i)]` is computable** — which is every revenue term in `docs/02`'s
objective. Provisional until then: A7 acquisition cost, N3's value interpretation, and
anything claiming to rank groups by expected profit.

**Missing: prices.** Probe Q2 confirms resource records carry exactly
`ankama_id, description, image_urls, level, name, pods, type` — no price, cost, or kama
field. `docs/02` states this independently ("No price data exists anywhere in the
repository today"). Consequences: `λ` stays user-set at 0.0; the `impact()` order-book
term is not computable; `c_i = Σ q_ir p_r` is not computable; and A3's "shared quantity"
cannot be converted to kama.

**Missing: market depth.** Without order-book data the impact term cannot be estimated,
so bulk-purchase penalties on the 34 broad resources (probe Q1) are unquantifiable.

**Missing: rarity/drop rates in the game-data sense.** Resources have a `level` field
(probe Q2: all 1642 non-null) but no drop-rate or rarity field. N1's `rarity(r) =
1/breadth(r)` is a *recipe-ubiquity* proxy, not a game rarity measure. It is the best
available proxy today, provisional in exactly the way the spec's open question 3
anticipates.

**Metrics that stay provisional until `break_log` / `price_cache` exist:**

| Metric | Blocked on | Status |
|---|---|---|
| A7 acquisition cost | λ + prices | Provisional; λ currently 0.0 so the term is inert |
| N3 weighted rune coverage (as value) | rune prices ρ_f | Structure valid, valuation provisional |
| Any profit estimate | ρ_f, c_i, τ, n_i | Not computable (docs/02 objective table) |
| N8 rarity-weighted overlap | rarity proxy only | Provisional until true rarity or prices |
| `flat_taux`-dependent ranking | break_log | Placeholder, documented as such |

**What IS solid now** and needs no new data: A1, A4, A5, A6, B1, B2, B7 (normalised per
N7), P1, P2, P3, P4, P8, and all of N1, N2, N4, N5, N6, N9, N10 — every one computable
from snapshot 3.7.7.6 alone, as the probes demonstrate.

---

## 6. Review status and implementation sequencing

**All review questions are closed. Decisions of record:**

| # | Question | Decision |
|---|---|---|
| 1 | Graph threshold | Build at **0.15**, splitter fixed in the same change. At 0.15 the largest component is 2807 items, so the splitter must be structure-aware or the change makes results worse. |
| 2 | Level ceiling | **1–200 permanent** planning/comparison default; 1–100 remains a job-level convenience scope. |
| 3 | N1 weighting | Report **both** `1/breadth` and `1/log(1+breadth)`; no preference committed. |
| 4 | Efficiency threshold | **Not legacy** — live via `policy.py:49`, mis-scoped as a general gate when it only discriminates at g=2,3. Rescope to a small-group floor; delete the dead 0.10 in `map_communities_inclusive`. |
| 5 | Genetic/evo experts | **Two of five are graph-bound** and cannot see 408 items (14.28%), spanning all 17 slots and all 11 bands. Fix by lowering the threshold, then the mutation fallback, then committee re-weighting, then per-expert coverage reporting. |
| 6 | Standing constraints | C1 large groups, C2 no set items, C3 shared resources. These set `max_line_items` as the primary lever and C2 as a pool-level exclusion. |
| 7 | Set exclusion | **Hard pool-level exclusion**, not a soft score term. `set_free_ratio` stays a reward as well. |
| 8 | Configurability | **`set_exclusion_min_size` configurable, default 5**, with an unfiltered override and the k-sweep (§3.8) as the reference for other values. |
| 9 |  Sequencing | Confirmed as below. |

**Implementation order (confirmed):**

1. **`max_line_items` 12 → 32 and `max_total_units` 500 → 2000** — pure config, no code
   change. Probe S3: lifts coverage **91.08% → 99.51%**. Also set `group_max_size`
   32 → 12 for consistency. Do this first; it is free.
2. **Structure-aware splitter + `graph_min_shared_ratio` 0.3 → 0.15** — one coupled
   change. Required before the threshold can move without regressions (FM1).
3. **`set_exclusion_min_size` = 5** with the `--no-set-filter` override and N10
   reporting. Independent of steps 1–2 (probe T5).
4. **Genetic mutation fallback** so evolution can seed from ungrouped items
   (`genetic_operators.py:145-150`).
5. **Objective term-set change** — drop `resource_reuse_ratio`, keep `compression` +
   `shared_quantity_ratio` + `set_free_ratio` (reward) − `largest_set_share` (penalty).
   Re-weighting deferred to a separate decision.

**Housekeeping, any time:** drop 15263 from `excluded_resource_ids` (dead, §3.5); wire
`get_active_pool` into the orchestrator before trusting `equipment_density_level_ratio`
(§3.4); add per-expert coverage to the run manifest (§3.7 rec 4).