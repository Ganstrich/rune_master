# Plan 15: Rewrite PROCESSING.md Documentation

## Goal
Rewrite `processing/PROCESSING.md` to accurately describe each expert, method, and the craft optimizer domain context.

## Current State
`PROCESSING.md` has several documentation gaps:
- Expert descriptions are vague ("Best for: Natural clusters")
- The group dict schema is incomplete (missing `fitness_score`, `seed_equipment_id`, etc.)
- `resource_optimizer.py` is listed as "placeholder" (will be removed or implemented)
- No explanation of *why* groups matter for crafting (domain context)
- No algorithm complexity information
- Configuration reference is scattered

## Approach
Rewrite `PROCESSING.md` with the following structure:

### 1. Overview
- What the processing module does (craft optimizer for Dofus equipment)
- Why grouping matters (batch crafting, shared ingredient gathering)
- Pipeline diagram: Equipment → Graph → Communities → Groups → Optimized Groups

### 2. Architecture
- Updated module tree (reflecting Plans 01-14 changes)
- Data flow diagram
- MoE (Mixture of Experts) architecture explanation

### 3. Configuration Reference
- Complete `ProcessingConfig` field documentation (single source of truth, after Plan 04)
- Default values and their rationale
- Example configurations for common use cases

### 4. Grouping Experts (one section per expert)
For each expert:
- **Algorithm**: What algorithm it uses (Louvain, stochastic, genetic)
- **Complexity**: Time/space complexity
- **Best for**: When to use it
- **Worst for**: When to avoid it
- **Parameters**: Which config fields affect it
- **Output**: What it produces

### 5. Group Dict Schema
- Complete field-by-field documentation
- Types and units for each field
- Which fields are added by which expert

### 6. Scoring Metrics
- `sharing_efficiency` — formula, range, interpretation
- `weighted_efficiency` — formula, why it's better
- `craftability_score` — formula, weights, interpretation
- `average_density` — formula, what it means for crafting

### 7. Craft Optimizer Domain
- What makes a "good" group for crafting (level band, profession, ingredient rarity)
- How the system optimizes for real crafting workflows
- Limitations and future work

## Files Affected
- `processing/PROCESSING.md` — complete rewrite

## Validation
- All experts described match their actual implementation (after all code changes)
- All config fields documented match `ProcessingConfig` dataclass
- Group dict schema matches what `create_group()` actually returns
- No references to removed modules (`resource_optimizer` if deleted in Plan 05)
