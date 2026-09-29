# Objective Model: What Makes A Group Good

See [README.md](README.md) for the status tag legend and
[01-domain-model.md](01-domain-model.md) for the mechanics this builds on.

## Summary

The objective is **profit from a production run**: buy resources in bulk, craft
a group of different items, break them for runes, sell the runes. Recipe overlap
is not the goal — it is the mechanism that makes broad, cheap exploration
affordable.

## Revenue

From [01-domain-model.md](01-domain-model.md), breaking an item with focus $f$
yields $\tau \cdot D_{\text{focus}}(f) / d_f$ runes of type $f$. Selling them:

$$R(\text{item}, f) = \tau \cdot D_{\text{focus}}(f) \cdot \rho_f
\qquad\text{where}\qquad
\rho_f = \frac{\text{market price of rune } f}{d_f}$$

**Everything reduces to price-per-density $\rho$.** **[INFERRED]**

Two consequences worth internalising:

**The guide's focus rule falls out of this.** Choosing focus $f$ over no focus
compares $D_{\text{focus}}(f)\rho_f$ against $\sum_s v_s d_s \rho_s$. Since focus
converts other lines at half rate, focusing wins when $\rho_f$ exceeds roughly
twice the density-weighted average $\rho$ of the other lines — which is exactly
what the guide states. The heuristic and the formula agree, which is mild
evidence the inferred model is right.

**The correct item scalar is not the current one.** **[VERIFIED-CODE]** The repo
computes `stat_weight` $= \sum_s v_s d_s$ in
[../processing/stat_calculator.py](../processing/stat_calculator.py). The
revenue-relevant quantity is $\sum_s v_s d_s \rho_s$. The existing value is the
$\rho \equiv 1$ special case — correct in structure, missing the price join.
This is the "coefficient" the project is chasing, and the table is already
built.

## Cost

$$c_i = \sum_r q_{ir}\, p_r$$

for recipe quantities $q_{ir}$ and resource prices $p_r$.

**[VERIFIED-CODE]** No price data exists anywhere in the repository today.
`models/resource.py` has no price field, `data/api_client.py` fetches no market
data, `data/cache_manager.py` has no price table, and
[../processing/quality_metrics.py](../processing/quality_metrics.py) is titled
"Price-independent quality features." The economic layer is entirely absent —
this is a greenfield addition, not a modification.

## Why Bulk Buying Helps — And The Correction

A natural assumption is that buying in bulk is cheaper per unit, so shared
resources reduce cost. **In a player-driven market this is backwards.** Filling
a large order walks up the sell-order book, so the marginal unit costs *more*,
not less. Sharing a resource across five items in a group means buying 5x as
much of it at a worse average price, and it concentrates liquidity risk on that
one resource.

The real, kama-denominated benefit of grouping is **fixed cost amortisation**:

1. Each *distinct* resource costs a market search, a price check, travel, and an
   inventory slot. Call its kama-equivalent $\lambda$.
2. A group with many items but few distinct resources spreads those fixed costs
   across more crafts.

So group compactness should be measured in **distinct line items**, not in
whether recipes happen to overlap pairwise.

**This unifies two things that look like competing goals.** Shopping-list
ergonomics is not a separate objective traded off against profit — it is the
$\lambda$ term *inside* the profit equation. There is no weight to hand-tune;
$\lambda$ is a measurable quantity, namely what a market round-trip is worth to
you. And $\lambda$-dominant is exactly the regime the system is in today, while
prices are unavailable — so a compactness proxy is the correct interim
objective and is not throwaway work.

## Taux Decay And Diversification

$\tau$ falls as an item type is broken. Writing $n_i$ for how many of item $i$
the plan produces, expected yield per unit is $\mathbb{E}[\tau_i(n_i)]$, which
is **decreasing in $n_i$**.

This produces the central tension:

| Force | Pushes toward |
| --- | --- |
| Taux decay | Many **different** item types |
| Acquisition fixed cost | Few **distinct** resources |

A group of many different items drawing on a small shared resource basket is the
object that satisfies both. This is why the group — not the item — is the unit
of optimisation, and it is a much stronger foundation than "shared resources are
convenient."

## The Full Objective

$$\text{Value}(G) = \sum_{i \in G} n_i\Bigl[\mathbb{E}[\tau_i(n_i)] \cdot D_i(f_i) \cdot \rho_{f_i} - c_i\Bigr]
\;-\; \lambda\Bigl|\bigcup_i R_i\Bigr|
\;-\; \text{impact}\Bigl(\textstyle\sum_i n_i q_{ir}\Bigr)$$

| Term | Meaning | Status |
| --- | --- | --- |
| $\mathbb{E}[\tau_i(n_i)]$ | Expected taux, decaying in own volume | **[UNKNOWN]** — needs measurement |
| $D_i(f_i)$ | Break density under chosen focus | **[VERIFIED-GAME]** formula |
| $\rho_{f_i}$ | Rune price per density | Needs a price feed |
| $c_i$ | Craft cost at spot | Needs a price feed |
| $\lambda \lvert\bigcup R_i\rvert$ | Fixed acquisition cost, per distinct resource | $\lambda$ is user-set |
| impact | Order-book walk, convex in quantity | Needs market depth |

**Note the objective is not additive over items.** Because $\tau_i$ depends on
$n_i$ and $\lambda$ applies to the *union* of resources, the value of adding an
item depends on what is already in the group. Any search procedure must respect
this — see the `marginal()` discussion in
[04-target-architecture.md](04-target-architecture.md).

## Exploration Is Part Of The Objective

Since $\tau$ is unobservable before breaking and decays with use, this is a
bandit problem: item types are arms, $\tau$ is an unknown and **rotting** reward
rate, and each break both reveals and degrades it.

The full theory is not required. The practical version:

1. Log every break outcome.
2. Maintain a posterior over $\tau$ per item type.
3. Have the objective use $\mathbb{E}[\tau]$ plus an **exploration bonus** for
   item types with few or no observations.

Under this framing, a group containing never-broken items is valuable *because*
of the information it produces, even if its point-estimate profit is mediocre.
That is precisely the project's stated purpose, and it should appear explicitly
in the objective rather than being left implicit.

## How Today's Score Relates

**[VERIFIED-CODE]** The current `quality_score` in
[../processing/quality_metrics.py](../processing/quality_metrics.py) is a
weighted blend of `resource_reuse_ratio`, `mean_pairwise_jaccard`,
`overlapping_pair_ratio`, and `shared_quantity_ratio`.

It is best understood as a **poor proxy for the $\lambda$ term alone**, ignoring
revenue, cost, taux, and impact entirely. It is a poor proxy because all four
features are scale-invariant ratios, so the score *decreases* with group size,
whereas the $\lambda$ term rewards fitting more items onto the same resource
basket. See [03-current-state-audit.md](03-current-state-audit.md), Failing 1.

The interim fix is a compactness measure that is extensive rather than
intensive:

$$\text{compression} = 1 - \frac{\left|\bigcup_i R_i\right|}{\sum_i |R_i|}$$

Zero for disjoint recipes, approaching $1 - 1/n$ for identical ones, and
increasing in $n$ — the correct gradient, and a direct stand-in for
$\lambda\lvert\bigcup R_i\rvert$ under constant prices.
