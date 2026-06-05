# Homepage Implementation Plan

## Overview
Create a new, stylish homepage that lets users input configuration parameters:
- Minimum level
- Maximum level
- One or more professions (addable via a click‑to‑add UI)

The plan is broken into **atomic, isolated actions** so each can be assigned to an implementer model.

---

## Atomic Action List

| # | Action | Description | Owner |
|---|--------|-------------|-------|
| 1 | Add homepage route | Define a new route `/home` in the web framework (e.g., Flask/FastAPI) that renders the homepage template. | Implementer |
| 2 | Create HTML template | Add `templates/home.html` with a clean layout, input fields for *min level*, *max level*, and a dynamic list for professions. | Implementer |
| 3 | Add CSS styling | Write `static/css/home.css` to give the page a professional look (responsive, modern UI components). | Implementer |
| 4 | Implement profession UI component | Use JavaScript to allow users to click **Add Profession** → creates a new input field, supports removal. | Implementer |
| 5 | Validate form data (client‑side) | Add JS validation for numeric ranges and non‑empty profession entries. | Implementer |
| 6 | Validate form data (server‑side) | In the route handler, verify `min <= max` and that at least one profession is provided; return errors if needed. | Implementer |
| 7 | Persist configuration | Store the submitted config in a JSON file or database table (`configurations`). | Implementer |
| 8 | Unit tests for route | Write tests that ensure the route returns 200, renders the template, and handles valid/invalid submissions. | Implementer |
| 9 | Integration test for UI flow | Use a headless browser (e.g., Playwright) to simulate adding professions, submitting, and checking persistence. | Implementer |
|10| Update documentation | Add a section in `README.md` describing the new homepage and its usage. | Implementer |

---

## Execution Notes
- Keep each action **self‑contained**: no action should modify files unrelated to its purpose.
- Follow the existing project structure: routes live in `rune_master/main.py`, templates under `templates/`, static assets under `static/`.
- Ensure all new files are added to version control.
- After completing actions 1‑7, run the test suite (`make test`) to verify nothing else broke.

---

*End of plan*