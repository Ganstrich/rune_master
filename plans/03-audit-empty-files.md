# Plan 03: Audit community_detector.py and resource_optimizer.py

## Goal
Verify that `community_detector.py` and `resource_optimizer.py` are not empty or corrupted.

## Current State
- `processing/community_detector.py` — returned empty content when read, but the code review showed it has content (~260 lines). Re-read to confirm.
- `processing/resource_optimizer.py` — returned empty content. Listed in `PROCESSING.md` as "Resource optimization (placeholder)". May be intentionally empty.

## Approach
1. **Re-read both files** with explicit line ranges to confirm their actual content
2. **For `community_detector.py`:**
   - If it has content: verify it matches the imports used by `graph_expert.py` (which imports `CommunityDetector`)
   - If empty/corrupted: restore from git history or rewrite
3. **For `resource_optimizer.py`:**
   - If intentionally empty: decide whether to delete it or implement it (see Plan 13)
   - If it should have content: restore or implement
4. **Check git status** — `git log --oneline -5 -- processing/community_detector.py processing/resource_optimizer.py` to see recent changes

## Files Affected
- `processing/community_detector.py`
- `processing/resource_optimizer.py`
## Validation
- Both files should either have valid Python content or be removed from the project
- `python -m py_compile processing/community_detector.py` — must succeed
- All imports of these modules must resolve
