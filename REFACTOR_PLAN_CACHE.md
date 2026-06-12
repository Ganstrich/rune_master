# Module: Refactor Plan: Replace JSON Cache with SQLite

## 1. Executive Summary & Purpose
- **Core Function:** Proposes replacing the current JSON cache file (`resource_cache.json`) with an auto-committed, concurrent-safe SQLite database (`resource_cache.db`). This improves load/save times, memory consumption, concurrency safety, and corruption resistance.
- **Target Audience/Users:** Developers implementing cache performance upgrades.
- **Design Philosophy:** Standard-library dependent (zero external dependencies via `sqlite3`), backward-compatible public API, and transaction-safe WAL mode concurrency.

## 2. Architectural & Structural Dependencies
- **Parent System/Universe:** RuneMaster
- **Inbound Dependencies:** None (architecture plan).
- **Outbound Dependencies:**
  - [data/DATA.md](file:///home/adamb/rune_master/data/DATA.md) (re-implements cache manager internals).
  - [config.py](file:///home/adamb/rune_master/config.py) (changes default cache filename).
- **Interactions/Data Flow:**
  API data and computed stats are saved via O(1) database inserts instead of rewriting large JSON objects. Callers get data using indexed queries.

## 3. Strict Rules & Mechanics (The "Hard Constraints")
| Parameter/State | Rule / Constraint | Logical Consequence |
| :--- | :--- | :--- |
| Public API Compatibility | Interface methods must match JSON `CacheManager` exactly | Bypasses the need to modify any callers of cache manager |
| SQLite Connection Mode | Must use write-ahead logging (`journal_mode=WAL`) | Allows concurrent reads and single-writer concurrency |
| ID Type | Tables keys must be integers | Removes `str()` key conversions necessary in JSON |
| `save()` method | Must remain present as a no-op | Avoids breaking backward-compatibility with callers |

## 4. Key Concepts & Terminology
- **Write-Ahead Logging (WAL):** SQLite mode that allows reading from the database while writing, protecting from concurrency crashes.
- **Auto-committed transactions:** Saves data immediately on insert, preventing mid-write truncation and corruption.

## 5. Known Gaps & Future Extensions
- **Established Backlog:** Clean up JSON files, update `.gitignore` to ignore sqlite temporary files (`*.db`, `*.db-wal`, `*.db-shm`), rewrite `data/cache_manager.py`.
- **[PROPOSITION]:** Implementing TTL-based expiration using `fetched_at` columns.
