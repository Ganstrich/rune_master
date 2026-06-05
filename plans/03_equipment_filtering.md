# Plan: Equipment Filtering by Level and Profession

## Files Affected
- `api_server.py` (modify — adds filtering logic to the recompute handler)
- `processing/config_dataclass.py` (modify — add min/max level fields)

## Summary
Add `min_level` and `max_level` to `ProcessingConfig` and implement filtering in the recompute pipeline so the API server can narrow equipment by level range and profession before running grouping.

## Actions

### Action 1: Add `min_level` / `max_level` to `ProcessingConfig`
- File: `processing/config_dataclass.py`
- Add two new fields to the `ProcessingConfig` dataclass:
  ```python
  min_level: int = 1
  max_level: int = 200
  ```
- Place them near the existing `min_equipment_density` field (equipment pre-filtering section)

### Action 2: Add level/profession filtering in `api_server.py` recompute handler
- File: `api_server.py`
- In the `POST /api/recompute` handler, after loading the full equipment list:
  1. Filter by profession: keep only equipment whose `type["name"]` matches one of the profession's item types
  2. Filter by level: keep only equipment where `min_level <= level <= max_level`
  3. Pass the filtered list to `RuneMaster` instead of the full list
- If the filtered list is empty, return an error response:
  ```json
  {"ok": false, "error": "No equipment matches the selected filters."}
  ```

## Design Decisions
- **Filtering happens in the server, not in `RuneMaster`**: The `RuneMaster` receives an already-filtered list. This keeps the processing pipeline unchanged and avoids coupling it to the API.
- **New config fields are optional defaults**: `min_level=1`, `max_level=200` means no filtering by default, preserving backward compatibility with `main.py` and the tuner.
