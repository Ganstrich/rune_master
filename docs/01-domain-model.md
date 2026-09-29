# Domain Model: Breaking Items For Runes

Source: <https://huzounet.fr/guides/forgemagie> (consulted 2026-09-29).
See [README.md](README.md) for the status tag legend.

This document covers **brisage** (breaking items for runes) only. Forgemagie
proper — placing runes on items, issues, priorities, reliquat, over/exo/
transcendance — is out of scope for RuneMaster and is deliberately omitted.

## Runes And Density

**[VERIFIED-GAME]** Every stat in the game maps to a rune type. Intelligence maps
to the Ine rune, and so on.

**[VERIFIED-GAME]** Each rune has a **density** (`densité`) reflecting its power.
Density governs how hard the rune is to obtain by breaking and how much it
affects forgemagie. Higher density means rarer and generally more valuable.

**[VERIFIED-GAME]** Most stats exist at three tiers:

| Tier | Example | Stat granted | Density |
| --- | --- | ---: | ---: |
| Minor | Rune Ine | +1 Intelligence | 1 |
| Medium (PA) | Rune Pa Ine | +3 Intelligence | 3 |
| Major (RA) | Rune Ra Ine | +10 Intelligence | 10 |

**[VERIFIED-GAME]** Fusion at the concasseur is 3:1 — `1 Ra = 3 Pa`,
`1 Pa = 3 minor`. Note the asymmetry: nine minor runes carry density 9 but fuse
into one Ra of density 10. Fusion therefore creates density. Which tier is most
profitable to *sell* is a price question, not a density question.

## The Density Table Already Exists In This Repository

**[VERIFIED-CODE]** `RUNE_DENSITY` in
[../processing/valuation/density.py](../processing/valuation/density.py) is the
rune density table. `stat_calculator.py` retains a compatibility alias for
callers. Representative entries:

```python
"PA": 100, "PM": 90, "Portée": 51, "Invocation": 30,
"Dommage": 5, "% Critique": 10, "Soin": 10,
"% Résistance terre": 6, "Résistance Terre": 2,
"Retrait PA": 7, "Esquive PA": 7, "Tacle": 4,
"Sagesse": 3, "Prospection": 3, "Puissance": 2,
"Force": 1, "Intelligence": 1, "Agilité": 1, "Chance": 1,
"Vitalité": 0.2, "Pod": 0.25, "Initiative": 0.1,
```

**[UNKNOWN]** The individual values have not been validated line by line against
a published density reference. The structure is clearly correct; specific
entries should be confirmed. This matters because density appears directly in
the revenue equation.

**Action:** rename the concept to `RUNE_DENSITY`, relocate it to the valuation
layer, and add a validation test. See
[04-target-architecture.md](04-target-architecture.md).

## The Taux De Brisage

This is the most important quantity in the entire system.

**[VERIFIED-GAME]** Rune yield from breaking depends on three things: the stats
present on the item, the item's level, and the item's **taux**.

**[VERIFIED-GAME]** The taux ranges from **1% to 4000%**.

**[VERIFIED-GAME]** The taux **cannot be known before breaking**. It is not
displayed and is not derivable from item properties.

**[VERIFIED-GAME]** The taux is **inversely related to how much that item has
been broken** — "moins un item est brisé et plus son taux sera haut."

**[VERIFIED-GAME]** The recommended player strategy is therefore to search,
test, and exploit: break widely to find items with a good taux, then break that
item repeatedly while the taux holds.

### Why This Defines The Project

A 40x range on a multiplier that no other term can compensate for means:

1. **An objective that ignores the taux is uninformative.** Every other factor —
   recipe cost, rune price, stat roll — is small next to a 1% versus 4000%
   swing.
2. **Profit is not linear in production volume.** Breaking an item type drives
   its own taux down, so crafting 200 of the best-known item is self-defeating.
3. **Discovery has value.** An unbroken item type has an unknown taux and is
   therefore an option worth paying to explore.
4. **Cheap variety is the enabling capability.** To discover high-taux items you
   must break many different items, and to afford that you need their recipes to
   overlap.

Point 4 is the economic justification for RuneMaster's entire grouping approach.

**[UNKNOWN]** Whether the taux attaches to the item *type* (server-wide, shared
across all players) or to the individual item *instance*. The guide's phrasing
about breaking the same object repeatedly implies type-level state with
server-wide decay, but this is not stated unambiguously and the distinction
changes the strategy substantially. **This should be resolved by observation
before Stage D.**

**[UNKNOWN]** Whether the taux recovers over time when an item type stops being
broken.

## Focus

**[VERIFIED-GAME]** When breaking, the player chooses either no focus (receive a
broad spread of runes matching the item's stats) or focus on exactly one rune.

**[VERIFIED-GAME]** The focus formula is given explicitly:

```text
Densité de brisage focus =
    densité(stat focus) + (densité(toutes les autres stats) / 2)
```

So for an item with stat lines $s$, each with rolled value $v_s$ and rune
density $d_s$:

$$D_{\text{no focus}} = \sum_s v_s d_s$$

$$D_{\text{focus}}(f) = v_f d_f + \tfrac{1}{2}\sum_{s \neq f} v_s d_s$$

Focusing converts half the density of every other line into the focused rune.

**[VERIFIED-GAME]** The guide's decision rule: focus is worthwhile when the
focused stat's price-to-density ratio is at least **twice** the average
price-to-density ratio of the item's other stats.

**[INFERRED]** That rule is a direct consequence of the formula above rather
than an independent heuristic — see
[02-objective-model.md](02-objective-model.md).

**Focus is a decision variable, not an item property.** The same item yields
different revenue depending on the chosen focus, and the best choice depends on
current rune prices. Any valuation of an item must state which focus it assumes.

## Rune Count Model

**[INFERRED]** The guide gives the density formula but not the conversion from
density to rune count. The model implied by it:

$$\text{runes}_f = \tau \cdot \frac{D_{\text{focus}}(f)}{d_f}$$

With no focus, each stat yields its own rune type in proportion to that line's
density contribution:

$$\text{runes}_s = \tau \cdot \frac{v_s d_s}{d_s} = \tau \cdot v_s$$

That is, without focus you receive roughly the taux fraction of each stat's
rolled value as runes of that stat.

**[UNKNOWN]** The guide states yield depends on item **level** as well as stats
and taux. The model above has no explicit level term — level enters only
implicitly, because higher-level items carry larger stat values. There may be an
additional level coefficient. **This is a primary calibration target.**

**[UNKNOWN]** Whether yield is deterministic given the taux or is itself
stochastic around an expectation.

## What Must Be Measured

These cannot be derived and must come from logged observation:

1. The conversion constant relating density to rune count, and any explicit
   level term.
2. Whether the taux is per-type or per-instance.
3. The decay curve of the taux against cumulative breaks.
4. Whether the taux recovers over time.

Design for this: see the `break_log` proposal in
[04-target-architecture.md](04-target-architecture.md). RuneMaster is, among
other things, an instrument for collecting this data.
