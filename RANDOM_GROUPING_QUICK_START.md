# Random Grouping Feature - Quick Start Guide

## Overview
RuneMaster now supports three grouping methods:
1. **Deterministic** - Original community detection approach
2. **Random** - New random selection with density filtering
3. **Hybrid** - Combines both methods

## Basic Usage

### Default (Deterministic - Original Behavior)
```bash
python main.py
```
Uses the original community detection algorithm.

### Random Grouping
```bash
python main.py --grouping-method random
```
Generates 10 random groups (default) by:
1. Filtering equipment by density/level ratio
2. Randomly selecting seed equipment
3. Finding companions that share resources with the seed

### Hybrid Grouping
```bash
python main.py --grouping-method hybrid
```
Runs deterministic first, then supplements with random groups if needed.

---

## Tuning Parameters

### Density/Level Ratio Filter
Controls which equipment are considered "high quality" based on stat power.

```bash
# More strict filter (smaller pool)
python main.py --grouping-method random --density-ratio 0.25

# Less strict filter (larger pool)
python main.py --grouping-method random --density-ratio 0.10

# No filter (all equipment)
python main.py --grouping-method random --density-ratio 0.0
```

**How it works:**
- Equipment must have: `stat_weight >= level * density_ratio`
- Default: 0.15 (15% of level)
- Higher ratio = fewer equipment in pool = more filtered
- If filtered pool < 10 items, automatically falls back to unfiltered

### Number of Random Groups
```bash
# Generate 20 random groups
python main.py --grouping-method random --random-groups 20

# Generate 5 random groups
python main.py --grouping-method random --random-groups 5
```

**Default:** 10 groups

### Combining Parameters
```bash
# Strict filter + many groups
python main.py --grouping-method random --density-ratio 0.20 --random-groups 15

# Loose filter + few groups
python main.py --grouping-method random --density-ratio 0.08 --random-groups 5

# Hybrid with custom filters
python main.py --grouping-method hybrid --density-ratio 0.18 --random-groups 12
```

---

## Understanding the Output

### Pool Filtering
When random grouping runs, you'll see:
```
[1/2] 📊 Applying Equipment Filtering...
      Active pool: 45 equipment (filtered)
```

This means:
- Started with 200 total equipment
- Density filter reduced pool to 45
- Using 45 for random selection

If pool is too small:
```
      Active pool: 150 equipment (unfiltered)
      ⚠️ Filtered pool too small. Falling back to unfiltered pool.
```

### Group Generation
```
[2/2] 🎲 Generating 10 Random Groups...
Generated group 1: Adamantine Sword + 5 companions
Generated group 2: Iron Boots + 3 companions
...
✅ Pipeline Complete: 10 random groups generated
```

---

## Finding Your Ideal Parameters

### Step 1: Check Default Density Distribution
```bash
python main.py --grouping-method random --density-ratio 0.15 --random-groups 5
```
Observe:
- What's the pool size after filtering?
- Are the groups interesting (good companion matches)?
- Is fallback happening?

### Step 2: Adjust Ratio to Target Pool Size
**Target pool size: 50-100 equipment**

- If filtered pool < 20: increase ratio (0.15 → 0.12)
- If filtered pool > 200: decrease ratio (0.15 → 0.18)
- If fallback always triggers: your ratio is too strict

```bash
# Testing different ratios
python main.py --grouping-method random --density-ratio 0.12  # Larger pool
python main.py --grouping-method random --density-ratio 0.18  # Smaller pool
python main.py --grouping-method random --density-ratio 0.22  # Much smaller
```

### Step 3: Tune Group Count
Once pool size is right, adjust random group count:

```bash
# Get good variety
python main.py --grouping-method random --density-ratio 0.15 --random-groups 20

# Get quick results
python main.py --grouping-method random --density-ratio 0.15 --random-groups 5
```

### Step 4: Try Hybrid for Best Results
```bash
# Combine deterministic + random
python main.py --grouping-method hybrid --density-ratio 0.15 --random-groups 10
```

---

## Understanding Group Efficiency

Each group shows:
- **Equipments**: List of items in group
- **Shared Resources**: Resources needed by entire group
- **Sharing Efficiency**: `unique_resources / total_requirements`
  - 0.5 = Good (50% reuse)
  - 0.3 = Okay (30% reuse)
  - 0.1 = Poor (10% reuse)

**Higher efficiency = better value** for bulk crafting.

---

## Troubleshooting

### Issue: "Filtered pool too small, using unfiltered"
**Cause:** Your density ratio is too strict for the equipment data

**Solution:**
- Lower the ratio: `--density-ratio 0.10` (was 0.15)
- Check if most equipment lacks stat_weight

### Issue: All random groups look similar
**Cause:** Equipment pool is too small or homogeneous

**Solution:**
- Try looser filter: `--density-ratio 0.10`
- Try more groups: `--random-groups 20`
- Check equipment data diversity

### Issue: Deterministic gives better results than random
**Cause:** Community detection finds natural clusters; random is more exploratory

**Solution:**
- Use hybrid mode: `--grouping-method hybrid`
- Or try looser filtering for more equipment: `--density-ratio 0.10`

---

## Examples for Different Use Cases

### Exploration (Find New Combinations)
```bash
python main.py --grouping-method random --density-ratio 0.10 --random-groups 20
```
- Uses loose filter for maximum variety
- Generates many groups
- Good for discovering unexpected combinations

### Optimization (Best Crafting Routes)
```bash
python main.py --grouping-method deterministic
# Or for supplemental groups:
python main.py --grouping-method hybrid --density-ratio 0.20 --random-groups 5
```
- Strict filter to focus on quality equipment
- Deterministic prioritizes natural clusters
- Few random groups for edge cases

### Balanced (Good of Both Worlds)
```bash
python main.py --grouping-method hybrid --density-ratio 0.15 --random-groups 10
```
- Default parameters
- Combines community detection + random selection
- Good quality groups + exploration

---

## Configuration via File (Advanced)

To make parameters permanent, edit `config.py`:

```python
class Config:
    # ...existing options...
    
    GROUPING_METHOD = "random"          # Default: "deterministic"
    DENSITY_LEVEL_RATIO = 0.18          # Default: 0.15
    RANDOM_GROUP_COUNT = 15             # Default: 10
    FALLBACK_TO_UNFILTERED = True       # Default: True
    MIN_FILTERED_POOL_SIZE = 10         # Default: 10
```

Then run without CLI flags:
```bash
python main.py  # Uses config.py settings
```

CLI arguments still override config file.

---

## Performance Notes

- **Random grouping:** Fast (O(n) per group)
- **Deterministic:** Slower but thorough (builds full graph)
- **Hybrid:** Medium speed (deterministic + some random)

For large equipment sets:
```bash
# Fast iteration during tuning
python main.py --grouping-method random --random-groups 5

# Full analysis when satisfied
python main.py --grouping-method hybrid --random-groups 15
```

---

## What to Do Next

1. **Try default random grouping:** `python main.py --grouping-method random`
2. **Test a few density ratios** to find ideal pool size
3. **Compare with deterministic:** `python main.py` (no flags)
4. **Try hybrid:** `python main.py --grouping-method hybrid`
5. **Fine-tune parameters** based on group quality and variety
6. **Update config.py** with your preferred defaults

Happy grouping! 🚀
