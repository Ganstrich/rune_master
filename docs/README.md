# RuneMaster Documentation

Context for future contributors and LLM agents. Read this file first.

## What RuneMaster Is For

RuneMaster proposes **groups of different equipment items whose recipes reuse the
same resources**, so a player can buy a short shopping list in bulk, craft many
varied items, break them for runes, and sell the runes at a profit.

The reason grouping is the right unit of work is not convenience. It follows
from the game mechanic:

- An item's **taux de brisage** (break rate, 1%-4000%) multiplies rune yield and
  **cannot be known before breaking it**.
- The taux falls as an item type is broken more across the server, so
  mass-producing a single known-good item degrades its own profitability.

Therefore the winning strategy is to craft **many different items cheaply** in
order to **discover** which ones currently carry a high taux, while keeping
acquisition cost low. Recipe overlap is what makes "many different items" cheap.
This is an exploration problem, and the group is the vehicle for exploration.

## Document Index

| Document | Contents |
| --- | --- |
| [01-domain-model.md](01-domain-model.md) | Brisage mechanics: rune density, focus, taux, rune tiers. Source-grounded. |
| [02-objective-model.md](02-objective-model.md) | The profit equation, acquisition cost, market impact, taux decay, exploration. |
| [03-current-state-audit.md](03-current-state-audit.md) | Concrete failings of the code as it stands, with file and line evidence. |
| [04-target-architecture.md](04-target-architecture.md) | Building blocks, the `GroupObjective` seam, module boundaries. |
| [05-roadmap.md](05-roadmap.md) | Staged plan, what each stage unblocks, open decisions. |

## Relationship To Other Specs

[../processing/PROCESSING.md](../processing/PROCESSING.md) remains the
**authoritative description of what the code currently does**. This folder
describes the *domain*, the *intended objective*, and the *target design*. Where
the two disagree, `PROCESSING.md` is right about the present and this folder is
right about the destination.

Do not edit `PROCESSING.md` to describe unimplemented behavior. Update it only
when the code changes.

## Status Legend

Every non-obvious claim in these documents is tagged. Respect the tags: several
important quantities are genuinely unknown, and treating an inference as a fact
is the most likely way to produce wrong work here.

| Tag | Meaning |
| --- | --- |
| **[VERIFIED-GAME]** | Stated directly by the cited game guide. |
| **[VERIFIED-CODE]** | Confirmed by reading the repository at the cited path. |
| **[INFERRED]** | A model derived from verified facts. Plausible, not confirmed. |
| **[UNKNOWN]** | Open question. Must be measured or researched before relying on it. |

## Primary Source

Forgemagie and brisage mechanics: <https://huzounet.fr/guides/forgemagie>
(consulted 2026-09-29, page last updated 2026-01-21).

This is a community guide, not official documentation. It is the best available
source, but any quantity taken from it that materially drives decisions should
be validated against in-game observation.
