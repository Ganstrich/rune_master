# Plan 09: Remove Dead Config Parameter `min_sharing_percentage`

## Problem
`min_sharing_percentage: int = 60` is defined in `ProcessingConfig` (line 36) but **never referenced** anywhere in the codebase. It's dead configuration that adds confusion.

## Decision
Remove the unused parameter. If it was intended for future use, it can be re-added when implemented.

## Atomic Actions

### Action 9.1: Remove `min_sharing_percentage` from `ProcessingConfig`
- **File:** `processing/config_dataclass.py`
- **Lines:** L36 (`min_sharing_percentage: int = 60`)
- **Change:** Delete the line.
- **Details:** Remove the entire line including the comment `# MIN_SHARING_PERCENTAGE`. No other files reference this parameter.
