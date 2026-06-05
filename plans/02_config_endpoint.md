# Plan: Config Bootstrap Endpoint

## Files Affected
- `api_server.py` (modify — same file as Plan 01, but a separate logical action)

## Summary
Add a `GET /api/config` endpoint that returns the current available options so the frontend can populate dropdowns dynamically.

## Actions

### Action 1: Add `GET /api/config` handler to `api_server.py`
- When the client sends `GET /api/config`, return a JSON response:
  ```json
  {
    "professions": [
      {"id": "bijoutier", "label": "Bijoutier", "types": ["ring", "amulet"]},
      {"id": "tailleur", "label": "Tailleur", "types": ["hat", "cloak"]},
      {"id": "forgeron", "label": "Forgeron", "types": ["sword", "hammer", "dagger", "axe", "shovel", "lance", "scythe"]},
      {"id": "sculpteur", "label": "Sculpteur", "types": ["staff", "wand", "bow"]},
      {"id": "faconneur", "label": "Faconneur", "types": ["shield"]},
      {"id": "cordonnier", "label": "Cordonnier", "types": ["boots", "belt"]}
    ],
    "grouping_methods": [
      {"id": "deterministic", "label": "Deterministic"},
      {"id": "random", "label": "Random"},
      {"id": "hybrid", "label": "Hybrid"},
      {"id": "committee", "label": "Committee"},
      {"id": "genetic", "label": "Genetic"}
    ],
    "level_range": {"min": 1, "max": 200}
  }
  ```
- Hardcode the profession list from `config.py` constants (single source of truth — import them)
- Hardcode the grouping methods list from `ProcessingConfig.grouping_method` choices
- Level range is static: 1–200 (Dofus max level)

## Design Decisions
- **Import from config.py**: Import `BIJOUTIER`, `TAILLEUR`, etc. from `config.py` to build the profession list, avoiding duplication.
- **Static level range**: 1–200 is a safe constant for Dofus. No need to compute from data.
