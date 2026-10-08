# Visualization

RuneMaster generates static HTML reports for equipment groups.

## Output

- `index.html` provides summary statistics and links to each group.
- `group_###.html` provides equipment details and the complete ingredient table.
- `static/` contains the shared CSS and JavaScript assets.

## HTMLGenerator

`HTMLGenerator` is responsible for:

- rendering equipment galleries with names, levels, and images;
- rendering ingredient totals and per-equipment quantities;
- generating the dashboard and group detail pages;
- copying shared static assets into the output directory.

Reports are self-contained apart from remote equipment and resource images. The
generator escapes user-facing text before inserting it into HTML.

## Validation

Generate reports without starting the server:

```bash
uv run main.py --no-serve
```

The generated index and group pages can then be served with any static HTTP
server for browser inspection.