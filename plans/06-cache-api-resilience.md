# Cache and API Resilience

## Objective

Make live data loading fail clearly and recover predictably without hiding stale or incomplete data.

## Scope

- Add bounded retries for transient API failures.
- Distinguish transport failures, invalid payloads, and missing resources.
- Report partial resource-cache failures in the generated metadata and CLI summary.
- Expose cache freshness or source status without changing the canonical metrics.
- Preserve offline operation of all processing and report tests.

## Acceptance Criteria

- Transient failures retry a bounded number of times with controlled delays.
- Permanent failures do not cause an infinite loop or silently fabricate data.
- A report identifies incomplete resource metadata when it occurs.
- Existing cached resources remain usable when the API is unavailable.

## Ownership

- Primary: `data/api_client.py`, `data/cache_manager.py`, and `main.py`
- Report status: `visualization/html_generator.py`
- Tests: offline transport/cache tests and a narrowly controlled live check

## Validation

- Test retry, timeout, malformed response, and cached fallback behavior offline.
- Run a live smoke test only when network access is available.
- Run the full working gate.

## Risks

Retries can increase runtime and third-party load. Use bounded attempts and make
failure state visible instead of optimizing only for successful runs.
