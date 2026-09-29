.PHONY: sync serve compute all tune clean help

# Install/update dependencies
sync:
	uv sync

# Default target
all: compute
	uv run main.py

# Start the visualization server only
serve:
	uv run serve.py

# Run quick for iterative development
dev:
	uv run main.py --no-serve

# Run the pipeline without starting the server
compute:
	uv run main.py --no-serve --grouping-method committee --tune

# Run with parameter tuning
tune:
	uv run main.py --no-serve --tune

# Run with a specific grouping method (usage: make method METHOD=hybrid)
method:
	uv run main.py --no-serve --grouping-method $(METHOD)

# Clean generated artifacts
clean:
	rm -rf visualizations/*.html visualizations/*.css
	rm -rf __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Show available targets
help:
	@echo "RuneMaster — available commands:"
	@echo ""
	@echo "  make sync         Install/update dependencies with uv"
	@echo "  make serve        Start the visualization server only"
	@echo "  make compute      Run the pipeline (no server)"
	@echo "  make dev          Run quick for iterative development"
	@echo "  make all          Run the pipeline and start the server"
	@echo "  make tune         Run with parameter tuning"
	@echo "  make method M=..  Run with a specific grouping method"
	@echo "                    M=deterministic|random|hybrid|committee|genetic"
	@echo "  make clean        Remove generated HTML/CSS and caches"
	@echo "  make help         Show this help message"
