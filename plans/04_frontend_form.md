# Plan: Frontend Config Form in Index Page

## Files Affected
- `visualization/html_generator.py` (modify — add form to index page)
- `visualization/static/index.css` (modify — add form styles)
- `visualization/static/utils.js` (modify — add form submission logic)

## Summary
Add an interactive configuration form to the index page dashboard that lets the user select min/max level, profession, and grouping method, then submit to recompute and refresh the results.

## Actions

### Action 1: Add config form HTML to `generate_index_page` in `html_generator.py`
- File: `visualization/html_generator.py`
- In the `generate_index_page` method, insert a `<form id="config-form">` block inside the `<header class="index-header">` section, after the subtitle `<p>` and before the `{summary_stats}` placeholder.
- The form should contain:
  - **Min Level**: `<input type="number" id="min_lvl" name="min_lvl" min="1" max="200" value="50">`
  - **Max Level**: `<input type="number" id="max_lvl" name="max_lvl" min="1" max="200" value="100">`
  - **Profession**: `<select id="profession" name="profession">` with options for each profession (populated from JS on load, or hardcoded)
  - **Grouping Method**: `<select id="grouping_method" name="grouping_method">` with options for each method
  - **Submit button**: `<button type="submit" class="btn btn-primary">Recompute</button>`
  - **Status indicator**: `<span id="recompute-status"></span>` for loading/error messages
- The form should be styled as a horizontal control bar (similar to the existing `.index-controls` pattern)

### Action 2: Add form styles to `index.css`
- File: `visualization/static/index.css`
- Add CSS rules for `#config-form` and its children:
  - Layout: `display: flex; flex-wrap: wrap; gap: var(--spacing-md); align-items: flex-end;`
  - Form groups: `.config-form-group` with `display: flex; flex-direction: column; gap: var(--spacing-xs);`
  - Labels: `.config-form-label` with small uppercase text
  - Inputs/selects: styled consistently with existing `.search-box` / `.sort-select` but with a solid background (not glass) for readability
  - Submit button: reuse `.btn-primary` styles
  - Status indicator: `.recompute-status` with color states (loading = blue, success = green, error = red)
  - Responsive: stack vertically on mobile

### Action 3: Add form submission JavaScript to `utils.js`
- File: `visualization/static/utils.js`
- Add a `DOMContentLoaded` handler that:
  1. Fetches `GET /api/config` to populate the profession and grouping method dropdowns
  2. Sets initial values from the current page state (read from URL query params or use defaults)
  3. Attaches a `submit` event listener to `#config-form`
- On form submit:
  1. Prevent default form submission
  2. Read form values
  3. Validate: min_lvl <= max_lvl, both in range 1–200
  4. Show loading state: disable button, show "Computing..." in status
  5. POST JSON to `/api/recompute` with `{ min_lvl, max_lvl, profession, grouping_method }`
  6. On success: show "Done! Refreshing..." then `window.location.reload()` after 500ms
  7. On error: show error message in status, re-enable button
- Use `fetch()` API (modern browser, no IE support needed)

## Design Decisions
- **Page reload on success**: The simplest approach — the server regenerates all HTML files, then the browser reloads to show the new index. No SPA complexity.
- **Dropdowns populated from API**: The profession and grouping method `<select>` elements are filled from `GET /api/config` on page load, so adding a new profession or method requires no frontend changes.
- **Form in the header**: Placing the config form in the header keeps it always visible and separate from the group cards grid.
