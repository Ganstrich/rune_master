# Job-Level Filtering

## Objective

Let the player configure their Dofus job levels so RuneMaster filters out
equipment they cannot craft. Groups and reports then contain only craftable
items, tailored to the player's situation.

## Current State

### Where filtering happens today

1. **API scope** (`config.py` + `main.py --min-level/--max-level`):
   Fetches only equipment within a level range. This is a blunt instrument —
   it applies one global range, not per-job ranges.

2. **Loader density filter** (`EquipmentLoader.from_raw_batch`):
   Applies `density_percentile` within level bands. This is a quality filter,
   not a craftability filter.

3. **Equipment filter** (`processing/equipment_filter.py`):
   Density/level ratio filtering used by the random expert. Also a quality
   filter, not craftability.

4. **No job-level concept exists anywhere in the codebase.** The gap is
   documented in `docs/00-goal-statement-and-clean-sate-todo.md` W7:
   > "Crafting requires a minimum profession level. The current pipeline
   > filters by item level but does not check whether the player's profession
   > level is sufficient to craft the items in a group."

### Job-to-type mapping (already in `config.py`)

```
CORDONNIER = boots, belt
BIJOUTIER  = ring, amulet
TAILLEUR   = hat, cloak
FORGERON   = sword, hammer, dagger, axe, shovel, lance, scythe
SCULPTEUR  = staff, wand, bow
FACONNEUR  = shield
```

Each of the 18 craftable item types maps to exactly one job. This mapping
already exists and is the foundation for the filter.

### Data flow

```
API/snapshot -> EquipmentLoader -> [density filter] -> RuneMaster -> experts -> groups
```

The filter needs to sit between the loader and RuneMaster, or inside
RuneMaster itself, so all experts benefit.

## Design

### Model

An equipment item of type T at level L is craftable if:

    player_level(job_for(T)) >= L

Where `job_for(T)` maps an item type to its job using the existing mapping
in `config.py`.

Items whose type is not in any job mapping (e.g., if new types are added)
are kept by default — they are not filtered out.

### Configuration

**New fields in `ProcessingConfig`:**

```python
# Job-level filtering
use_job_level_filter: bool = False
job_levels: dict = field(default_factory=dict)  # e.g. {"forgeron": 120, "bijoutier": 80}
```

**New file `player_config.json` (optional, persistent):**

```json
{
  "job_levels": {
    "forgeron": 120,
    "bijoutier": 80,
    "cordonnier": 100,
    "tailleur": 90,
    "sculpteur": 110,
    "faconneur": 70
  }
}
```

Loaded at startup if present. CLI args override file values.

**New CLI arg:**

```
--job-levels "forgeron:120,bijoutier:80,cordonnier:100"
```

Comma-separated `job:level` pairs. Overrides `player_config.json` values
for the specified jobs.

### New module: `processing/job_filter.py`

```python
class JobLevelFilter:
    """Filter equipment by player job levels."""
    
    # Built from config.py mappings
    JOB_TO_TYPES = {
        "cordonnier": {"boots", "belt"},
        "bijoutier": {"ring", "amulet"},
        "tailleur": {"hat", "cloak"},
        "forgeron": {"sword", "hammer", "dagger", "axe", "shovel", "lance", "scythe"},
        "sculpteur": {"staff", "wand", "bow"},
        "faconneur": {"shield"},
    }
    
    TYPE_TO_JOB = {t: job for job, types in JOB_TO_TYPES.items() for t in types}
    
    @staticmethod
    def filter_equipments(
        equipments: List[Equipment],
        job_levels: Dict[str, int],
    ) -> tuple[List[Equipment], List[Equipment]]:
        """Return (craftable, filtered_out)."""
        ...
    
    @staticmethod
    def can_craft(equipment: Equipment, job_levels: Dict[str, int]) -> bool:
        """Check if a single equipment is craftable."""
        ...
```

### Integration point

**In `main.py`**, after `load_equipment()` and before `process_equipment()`:

```python
if processing_config.use_job_level_filter and processing_config.job_levels:
    craftable, filtered = JobLevelFilter.filter_equipments(equipments, processing_config.job_levels)
    print(f"  Job-level filter: {len(craftable)} craftable, {len(filtered)} filtered out")
    equipments = craftable
```

This is the single insertion point. All downstream experts (deterministic,
random, genetic, greedy, committee, evolutionary) automatically see only
craftable items.

### Snapshot path

The same filter is applied when loading from a snapshot. In `main.py`, the
filter runs after `load_snapshot()` returns equipment, using the same
`JobLevelFilter.filter_equipments()` call. No changes needed in
`data/snapshot.py` itself.

### What is NOT changed

- **API client** (`data/api_client.py`): No changes. The API still fetches
  the full level range; filtering happens after load. This keeps the API
  client simple and the filter reusable across live/snapshot paths.
- **Experts** (`processing/experts/`): No changes. They receive the
  already-filtered pool.
- **Policy** (`processing/policy.py`): No changes. Policy thresholds are
  orthogonal to craftability.
- **Graph builder** (`processing/graph_builder.py`): No changes.
- **Reports** (`visualization/html_generator.py`): No changes. Reports
  already show whatever groups they receive.

## File changes

| File | Change |
|---|---|
| `processing/config_dataclass.py` | Add `use_job_level_filter: bool = False` and `job_levels: dict = field(default_factory=dict)` |
| `processing/job_filter.py` | **New.** `JobLevelFilter` class with `filter_equipments()`, `can_craft()`, and job-to-type mapping |
| `main.py` | Add `--job-levels` CLI arg; load `player_config.json` if present; apply `JobLevelFilter` after equipment load |
| `player_config.json` | **New.** Optional persistent config file |
| `test/test_job_filter.py` | **New.** Offline tests for the filter |
| `processing/PROCESSING.md` | Document the new config fields and filter behavior |
| `README.md` | Document the new CLI arg and config file |
| `config.py` | No changes (mapping already exists) |
| `data/snapshot.py` | No changes (filter applied in main.py) |

## Acceptance Criteria

1. When `use_job_level_filter=False` (default), behavior is identical to
   today — no filtering, full pool.
2. When `use_job_level_filter=True` and `job_levels` is populated, only
   items where `player_level(job_for(type)) >= item.level` are kept.
3. Items with types not in the job mapping are kept (not filtered).
4. `--job-levels "forgeron:120"` overrides the config file for that job.
5. The filter count (craftable / filtered out) is printed in CLI output.
6. The effective job levels are recorded in the run manifest.
7. Offline tests cover: all jobs mapped, unknown types kept, empty
   job_levels dict (no filtering), boundary condition (level == job
   level), and CLI parsing.
8. Both live API and snapshot paths apply the filter.
9. The working gate stays green: `uv run pytest -q`.

## Risks

- **Job-to-type mapping drift:** If Dofus 3 adds new item types or changes
  job associations, the mapping in `config.py` must be updated. The filter
  silently keeps unknown types, so new types would appear even if the
  player hasn't configured that job. This is a known tradeoff — better to
  show too much than too little.
- **Config file discovery:** `player_config.json` is loaded from the
  project root. If the user runs from a different directory, it won't be
  found. This can be resolved later with an explicit `--config` path.


## Wiki updates

- Record the W7 gap as addressed in `concepts/rune-master-roadmap.md`.
- Note the design decision (filter at pipeline entry, not at API level) in
  the runemaster entity page or a new concept page if it proves
  non-obvious.
- Update `log.md` with the plan creation.
