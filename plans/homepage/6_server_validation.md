# Plan 6: Validate form data (server-side)

- Update the route handler in `rune_master/main.py`.
- Handle POST requests for the `/home` form.
- Validate `min_level` and `max_level` range and logic.
- Validate that the list of professions is non-empty.
- Return appropriate status codes and error messages for invalid input.
