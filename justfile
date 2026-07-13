# Run all checks
all: format lint typecheck test

# Format code
format:
    uv run ruff format src/ tests/

# Lint code
lint:
    uv run ruff check src/ tests/

# Type check
typecheck:
    uv run ty check src/

# Run tests
test:
    uv run pytest

# Run tests with coverage
cov:
    uv run pytest --cov=dsz
