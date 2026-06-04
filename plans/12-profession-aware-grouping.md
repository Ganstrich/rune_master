# Plan 12: Add Profession-Aware Grouping

## Goal
Group equipment by crafting profession so that each group contains items craftable by the same profession.

## Current State
`config.py` defines profession-to-item-type mappings:
```python
CORDONNIER = ["boots", "belt"]
BIJOUTIER = ["ring", "amulet"]
TAILLEUR = ["hat", "cloak"]
FORGERON = ["sword", "hammer", "dagger", "axe", "shovel", "lance", "scythe"]
SCULPTEUR = ["staff", "wand", "bow"]
FACONNEUR = ["shield"]
```

These mappings exist but are **never used** by any grouping algorithm. The `Config.ITEM_TYPES` filter restricts which equipment types are loaded (default: `BIJOUTIER`), but within that filter, no profession-level grouping occurs.

## Problems
- A group might contain a ring and a belt — different professions, can't be crafted by the same person
- The `ITEM_TYPES` filter in `config.py` limits to one profession at a time, but this is a blunt instrument (all or nothing)
- No expert uses profession information to score or filter groups

## Approach
1. **Add a `group_by_profession` config flag** to `ProcessingConfig`:
   ```python
   group_by_profession: bool = True  # Only group items craftable by the same profession
   ```

2. **Build a profession lookup** in `GroupMapper.__init__()`:
   ```python
   self.profession_map = {}
   for profession, types in PROFESSION_TYPES.items():
       for item_type in types:
           self.profession_map[item_type] = profession
   ```

3. **Add a profession check** in `map_communities()` and `map_communities_inclusive()`:
   - Before processing a community, determine the profession of each item (via `equipment.type["name"]`)
   - If `group_by_profaction` is True, split the community by profession before applying size/quality filters
   - Each profession subgroup is processed independently

4. **Add profession metadata** to the group dict:
   ```python
   "profession": "Bijoutier",  # or None if mixed
   ```

5. **Update the random expert** to filter companions by profession match with the seed

6. **Update the genetic expert** fitness function to give a bonus to single-profession groups

## Files Affected
- `processing/config_dataclass.py` — add `group_by_profession` field
- `processing/group_mapper.py` — add profession lookup and filtering
- `processing/random_group_builder.py` — filter companions by profession
- `processing/experts/genetic_expert.py` — profession bonus in fitness
- `config.py` — the profession mappings already exist, just need to be imported

## Validation
- Run the deterministic pipeline with `group_by_profession=True` and verify all groups contain items of a single profession
- Run with `group_by_profession=False` and verify behavior is unchanged
- Verify the profession field appears in group visualizations
