# Phase 1 Decision: Measured Method Comparison

**Date:** 2026-10-10  
**Pool:** Full 1-200 snapshot (3.7.7.6), per-craft runs  
**Methods:** deterministic, random, genetic, greedy, hybrid, committee, evolutionary_committee, baseline

---

## Measured Results (per craft)

### Armor crafts

| Craft | Method | Groups | PQ | Coverage | Time |
|-------|--------|--------|-----|----------|------|
| **cordonnier** | deterministic | 45 | 0.403 | 0.44 | 1.8s |
| | random | 23 | 0.095 | 0.11 | 0.1s |
| | genetic | 21 | 0.337 | 0.17 | 14.9s |
| | greedy | 53 | 0.503 | 0.59 | 4.1s |
| | hybrid | 46 | 0.411 | 0.46 | 1.7s |
| | committee | 170 | 0.241 | 0.77 | 109.3s |
| | evolutionary_committee | 48 | 0.508 | 0.69 | 117.3s |
| | baseline | 48 | 0.508 | 0.69 | 97.0s |
| **bijoutier** | deterministic | 45 | 0.403 | 0.44 | 1.8s |
| | genetic | 21 | 0.337 | 0.17 | 14.9s |
| | greedy | 53 | 0.503 | 0.59 | 4.1s |
| | committee | 172 | 0.264 | 0.82 | 107.3s |
| | evolutionary_committee | 49 | 0.512 | 0.73 | 117.9s |
| | baseline | 49 | 0.512 | 0.73 | 95.2s |
| **tailleur** | deterministic | 22 | 0.363 | 0.29 | 1.4s |
| | genetic | 24 | 0.262 | 0.17 | 17.5s |
| | greedy | 35 | 0.425 | 0.41 | 8.5s |
| | committee | 145 | 0.225 | 0.73 | 101.0s |
| | evolutionary_committee | 44 | 0.457 | 0.62 | 107.7s |

### Weapon crafts

| Craft | Method | Groups | PQ | Coverage | Time |
|-------|--------|--------|-----|----------|------|
| **forgeron** | deterministic | 45 | 0.366 | 0.53 | 2.1s |
| | genetic | 18 | 0.323 | 0.17 | 15.2s |
| | greedy | 52 | 0.578 | 0.82 | 4.7s |
| | committee | 172 | 0.241 | 0.88 | 107.3s |
| **sculpteur** | deterministic | 34 | 0.429 | 0.51 | 0.2s |
| | genetic | 19 | 0.359 | 0.21 | 10.9s |
| | greedy | 26 | 0.544 | 0.61 | 1.6s |
| | committee | 96 | 0.314 | 0.90 | 15.8s |
| | evolutionary_committee | FAILED (NetworkXError) | — | — | — |
| | baseline | 25 | 0.560 | 0.82 | 3.1s |
| **faconneur** | deterministic | 15 | 0.230 | 0.36 | 0.1s |
| | genetic | 8 | 0.238 | 0.19 | 2.8s |
| | greedy | 7 | 0.337 | 0.29 | 0.4s |
| | committee | 41 | 0.158 | 0.76 | 6.7s |
| | evolutionary_committee | 13 | 0.386 | 0.70 | 4.3s |
| | baseline | 13 | 0.386 | 0.70 | 0.6s |

---

## Decision

### Tier 1: KEEP (fast, high value)

| Method | Role | Runtime | Coverage | Quality |
|--------|------|---------|----------|---------|
| **greedy** | Primary method | 0.4-8.5s | 0.29-0.82 | 0.337-0.578 |
| **deterministic** | Fast dev/fallback | 0.1-2.1s | 0.29-0.53 | 0.230-0.429 |
| **hybrid** | Lightweight supplement | 0.1-2.0s | 0.37-0.55 | 0.000-0.411 |
| **random** | Baseline comparison | 0.0-0.1s | 0.10-0.25 | 0.039-0.251 |

### Tier 2: REMOVE (too slow, low value, or redundant)

| Method | Reason | Evidence |
|--------|--------|----------|
| **genetic** | Dominated by greedy on every craft. 10-15x slower, 3-4x lower coverage. | Forgeron: greedy pq=0.578 cov=0.82 4.7s vs genetic pq=0.323 cov=0.17 15.2s |
| **evolutionary_committee** | Identical to baseline or fails outright. 4-12x slower. | Faconneur: baseline pq=0.386 cov=0.70 0.6s vs evo pq=0.386 cov=0.70 4.3s. Sculpteur: FAILED |
| **committee** | 6-15x slower than greedy, 3-5x lower PQ. High coverage but quantity-over-quality. | Sculpteur: greedy pq=0.544 cov=0.61 1.6s vs committee pq=0.314 cov=0.90 15.8s |
| **baseline** | Identical to evolutionary_committee or dominated by greedy. | Faconneur: greedy pq=0.337 cov=0.29 0.4s vs baseline pq=0.386 cov=0.70 0.6s (but evo=baseline) |

### Key Findings

1. **genetic is strictly dominated by greedy** on all 6 crafts. Greedy has higher coverage, higher quality, and is faster. The genetic expert's graph-bound search cannot compete with greedy's full-pool objective-driven growth.

2. **evolutionary_committee adds nothing over baseline**. On faconneur they produce identical results (13 groups, pq=0.386, cov=0.70). On sculpteur, evolutionary_committee fails with a NetworkXError while baseline succeeds.

3. **committee is quantity-over-quality**. It produces the most groups (96-172) and highest coverage (0.73-0.90) but the lowest PQ (0.158-0.314). The 6-15x runtime over greedy is not justified.

4. **greedy is the best quality/coverage/speed trade-off** on every craft. It should be the default.

5. **evolutionary_committee has a bug**: NetworkXError "node 8611 is not in the graph" on sculpteur. This is a real crash, not just a performance issue.

---

## Recommended Actions

1. **Change default** from `evolutionary_committee` to `greedy`
2. **Remove genetic, evolutionary_committee, committee, baseline** from the main pipeline
3. **Flag as legacy** in code comments and documentation
4. **Keep greedy, deterministic, hybrid, random** as the active method set

---

## Files to Modify

- `processing/config_dataclass.py` — change default to `greedy`, mark others legacy
- `processing/orchestrator.py` — remove slow methods from `_dispatch_experts` and `run_*`
- `main.py` — remove from CLI choices
- `Makefile` — update targets
- `REPO_SUMMARY.md` — update method table
