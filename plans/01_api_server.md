# Plan: API Server for Dynamic Recomputation

## Files Affected
- `serve.py` (modify)
- New file: `api_server.py`

## Summary
Replace the static-only `serve.py` HTTP server with a lightweight API server that can:
1. Serve static visualization files (existing behavior)
2. Accept POST requests with new config parameters (min_lvl, max_lvl, profession, grouping_method)
3. Re-run the processing pipeline with those parameters
4. Return the new groups as JSON so the frontend can refresh

## Actions

### Action 1: Create `api_server.py` — new lightweight HTTP server with API endpoint
- Create a new file `api_server.py` at project root
- Implement a `http.server`-based server (no new dependencies) with two modes:
  - `GET` → serves static files from `visualizations/` (same as current `serve.py`)
  - `POST /api/recompute` → accepts JSON body, runs pipeline, returns JSON result
- The POST handler should:
  1. Parse JSON body: `{ "min_lvl": int, "max_lvl": int, "profession": str, "grouping_method": str }`
  2. Build a `ProcessingConfig` with the given `grouping_method`
  3. Filter the cached equipment list by `min_lvl`/`max_lvl` and profession (item type)
  4. Re-run `RuneMaster` processing
  5. Regenerate visualizations via `HTMLGenerator`
  6. Return JSON: `{ "ok": true, "groups_count": int, "index_path": str }`
- Use `http.server.HTTPServer` with a custom `BaseHTTPRequestHandler` subclass
- Support `--port` CLI argument (default 8000)
- Support `--no-open` flag to skip browser launch

### Action 2: Update `serve.py` — delegate to `api_server.py`
- Replace the server logic in `serve.py` to simply import and call `api_server.start_server()`
- Keep the existing CLI interface (`serve.py [port]`) so existing workflows still work
- This is a backward-compatible shim

## Design Decisions
- **No new dependencies**: Use stdlib `http.server` + `json` to avoid adding Flask/FastAPI
- **Synchronous recompute**: The POST handler blocks while processing runs. This is acceptable because the server is single-user local. For long runs, the frontend will wait.
- **Equipment caching**: The server should hold a module-level cache of the last loaded equipment list so recompute calls don't re-fetch from API every time. Use a simple global dict `_state = { "equipments": [...], "cache": ..., "api": ... }` populated on first call.
- **Profession → item type mapping**: Use the existing `config.py` profession constants (`BIJOUTIER`, `TAILLEUR`, `FORGERON`, `SCULPTEUR`, `FACONNEUR`, `CORDONNIER`). The profession string maps to a list of item type names that becomes `ITEM_TYPES`.
