# Plans

This directory holds the project's active plans, organized by category:

- **refactor/** — restructuring or cleanup of existing code, no new features
- **backlog/** — planned features or work not started yet (or started and paused)
- **upgrade/** — improvements or extensions to existing features, dependency or tooling upgrades
- **research/** — hypotheses, investigations, experiments, open questions (no committed implementation)

Each plan carries a YAML frontmatter header with status, last review date, and related documents.

---

## research/

| Plan | Status | Summary |
|------|--------|---------|
| `group-evaluation-spec.md` | backlog | Metric taxonomy for comparing grouping methods on two axes: shopping-list efficiency and exploration diversity |
| `pipeline-challenge.md` | in-progress | Challenge the pipeline with 9 new metrics (M1–M9); partial results in `data/plans/challenge-results.json` |
| `data-profile.md` | reference | Full snapshot profile (3.7.7.6): 2858 equipment, 1642 resources, 3646 set mappings |

---

## refactor/

| Plan | Status | Summary |
|------|--------|---------|
| *(none)* | — | — |

---

## backlog/

| Plan | Status | Summary |
|------|--------|---------|
| `pipeline-challenge-update.md` | backlog | Update pipeline-challenge.md for the 5 active methods (4 removed in 82a32ba) |
| `quality-score-reweighting.md` | backlog | Propose new weights for the 4-term quality_score blend (deferred in metrics-revision.md) |

---

## upgrade/

| Plan | Status | Summary |
|------|--------|---------|
| *(none)* | — | — |
