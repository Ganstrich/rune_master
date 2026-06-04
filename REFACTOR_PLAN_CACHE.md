# Refactor Plan: Replace JSON Cache with SQLite

## Problem

The current `CacheManager` in `data/cache_manager.py` uses a single JSON file (`resource_cache.json`, ~11K lines, ~1.1MB) as a persistent cache. This has several issues:

1. **Slow load/save** — Every `save()` rewrites the entire JSON file with `json.dump(..., indent=2)`. As the cache grows, this gets progressively slower (O(n) write for every change).
2. **No partial reads** — `_load_from_disk()` parses the entire JSON into memory even if you only need one resource.
3. **No concurrency safety** — The docstring itself warns "safe for concurrent reads (but not concurrent writes)." The `tuner.py` uses `ProcessPoolExecutor` with multiple processes hitting the same JSON file.
4. **Fragile corruption handling** — If the process is killed mid-write, the JSON file can be truncated/corrupted, and the whole cache is lost.
5. **Stringly-typed keys** — All IDs are stored as strings (`str(resource_id)`) because JSON only supports string keys, requiring constant conversion.

## Solution: SQLite via `sqlite3` (stdlib)

Replace the JSON file with a SQLite database. This gives us:

| Property | JSON (current) | SQLite (proposed) |
|---|---|---|
| **Read one entry** | Parse entire file | `SELECT ... WHERE id=?` (O(1) lookup) |
| **Write one entry** | Rewrite entire file | `INSERT OR REPLACE` (O(1) amortized) |
| **Concurrency** | Not safe for writes | WAL mode: concurrent reads + single writer |
| **Corruption risk** | High (truncated write = total loss) | Low (WAL journaling is crash-safe) |
| **Memory** | Entire cache loaded at init | Only queried rows loaded |
| **Dependencies** | `json` (stdlib) | `sqlite3` (stdlib) — **zero new deps** |
| **Disk format** | Human-readable text | Binary (not human-editable) |

### Why SQLite over alternatives

- **`shelve`** — Still loads entire file on some backends, not concurrency-safe, pickle-based (security/versioning concerns).
- **`diskcache` / `lmdb` / `rocksdb`** — External dependencies, overkill for this use case.
- **`msgspec` / `orjson` faster JSON** — Still has the full-rewrite problem.
- **SQLite** — In the Python stdlib since 2.5, battle-tested, WAL mode is perfect for read-heavy + occasional-write workloads like this.

## New Cache Schema

```sql
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    data BLOB NOT NULL,       -- msgpack or json blob of the full API response
    fetched_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS equipment_effects (
    equipment_id INTEGER PRIMARY KEY,
    effects BLOB NOT NULL,     -- JSON blob of effects list
    fetched_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stat_weights (
    equipment_id INTEGER PRIMARY KEY,
    weight REAL NOT NULL,
    computed_at TEXT DEFAULT (datetime('now'))
);
```

- `resources.id` is the Ankama ID (integer, no more `str()` conversion).
- `data` / `effects` are stored as JSON strings inside BLOB columns (no need for msgpack — `json.dumps`/`loads` is fine since we only read/write whole values).
- `fetched_at` / `computed_at` columns enable TTL-based expiry (future improvement).

## New `CacheManager` API

The public API stays **identical** — same method names, same signatures, same return types. This is a drop-in replacement:

```python
class CacheManager:
    def __init__(self, cache_file: str = Config.CACHE_FILE): ...
    def get_resource(self, resource_id: int) -> Optional[Dict]: ...
    def set_resource(self, resource_id: int, data: Dict) -> None: ...
    def has_resource(self, resource_id: int) -> bool: ...
    def get_resource_name(self, resource_id: int) -> Optional[str]: ...
    def get_equipment_effects(self, equipment_id: int) -> Optional[list]: ...
    def set_equipment_effects(self, equipment_id: int, effects: list) -> None: ...
    def has_equipment_effects(self, equipment_id: int) -> bool: ...
    def get_stat_weight(self, equipment_id: int) -> Optional[float]: ...
    def set_stat_weight(self, equipment_id: int, weight: float) -> None: ...
    def has_stat_weight(self, equipment_id: int) -> bool: ...
    def get_stats(self) -> Dict[str, int]: ...
    def clear(self) -> None: ...
    def save(self) -> None: ...  # No-op (auto-committed), kept for API compat
    @property
    def cache_file(self) -> str: ...  # Still exposed (tuner.py reads it)
```

Key changes under the hood:
- `__init__` opens a SQLite connection, creates tables if needed. No full load.
- Each `get_*` does a `SELECT` query (returns only the requested row).
- Each `set_*` does `INSERT OR REPLACE` (auto-committed via WAL mode).
- `save()` is a no-op (kept for backward compatibility — `main.py` calls it).
- `cache_file` property still returns the path string (used by `tuner.py` to pass to worker processes).
- `get_stats()` does `SELECT COUNT(*) FROM ...` on each table.

## Migration Strategy

### Phase 1: Implement new SQLite CacheManager

1. **Write `data/cache_manager.py`** with the new SQLite-backed implementation.
   - Keep the exact same public API.
   - Use `sqlite3.connect()` with `journal_mode=WAL` and `synchronous=NORMAL`.
   - Store the `.db` file alongside the old `.json` file (new default: `resource_cache.db`).
   - On first run with the new code, the old JSON file is simply ignored (cache starts empty and rebuilds from API calls).

2. **Update `config.py`** — Change `CACHE_FILE` default:
   ```python
   CACHE_FILE = 'resource_cache.db'  # was 'resource_cache.json'
   ```

3. **Update `data/__init__.py`** — No changes needed (still exports `CacheManager`).

### Phase 2: Update all callers (no API changes needed)

Since the public API is identical, callers need **zero changes**:

| File | Usage | Change |
|---|---|---|
| `data/loaders.py` | `CacheManager()` default init | None |
| `main.py` | `CacheManager(cache_file=Config.CACHE_FILE)` | None (config value changes) |
| `main.py` | `cache.save()` | None (no-op now) |
| `processing/orchestrator.py` | Passes `cache_manager` through | None |
| `processing/tuner.py` | `self.cache_manager.cache_file` | None (property still exists) |
| `processing/tuner.py` | `CacheManager(cache_file=cache_file)` in workers | None |
| `processing/experts/*.py` | `self.cache_manager` | None |

### Phase 3: Cleanup

1. **Delete `resource_cache.json`** (or move to `resource_cache.json.bak`).
2. **Update `.gitignore`** — Add `*.db`, `*.db-wal`, `*.db-shm`.
3. **Update documentation** — `copilot.instructions.md` and `MODULE_REFERENCE.md` references to the JSON cache.
4. **Remove the old JSON file** from the repo if it was committed.

## Files Changed

| File | Change |
|---|---|
| `data/cache_manager.py` | **Rewritten** — SQLite backend, same public API |
| `config.py` | `CACHE_FILE` default changes from `.json` to `.db` |
| `.gitignore` | Add `*.db`, `*.db-wal`, `*.db-shm` |
| `.github/instructions/copilot.instructions.md` | Update cache references |
| `.github/instructions/MODULE_REFERENCE.md` | Update cache references |

## What's NOT Changed

- **Public API** — Every caller of `CacheManager` works unchanged.
- **Cache semantics** — Still a disk-based persistent cache, still keyed by integer IDs.
- **Behavior** — `has_*` checks, `get_*` returns `None` on miss, `set_*` stores — all identical.
- **Dependencies** — `sqlite3` is in the stdlib. No new packages.
- **The `save()` method** — Kept as a no-op for backward compatibility.

## Performance Expectations

| Operation | JSON (current) | SQLite (new) |
|---|---|---|
| Startup (load) | ~50ms parse + ~1MB alloc | ~0.1ms (connect only) |
| `get_resource(id)` | Dict lookup in memory (fast) | Indexed query (~0.05ms) |
| `set_resource(id, data)` | Rewrite entire file (~50ms) | Single INSERT (~0.1ms) |
| `get_stats()` | `len()` on 3 dicts | 3x `COUNT(*)` (~0.1ms) |
| Memory at startup | ~1MB+ (full JSON) | ~0KB (connection only) |
| Concurrent reads (tuner) | Race conditions | WAL mode: safe |

## Validation

1. `python -m pytest test/` — All existing tests pass (API is identical).
2. `python main.py --no-serve` — Full pipeline runs, cache rebuilds from API on first run.
3. `python main.py --no-serve` (second run) — Cache hits from SQLite, no API calls for cached items.
4. `python main.py --grouping-method committee --no-serve` — Concurrent expert processes read from SQLite safely.
5. `python -c "from data import CacheManager; c = CacheManager(); print(c.get_stats())"` — Shows correct counts.
