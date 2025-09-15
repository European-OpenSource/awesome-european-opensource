# Setup the development environment
setup:
    @uv venv --python 3.12
    @uv sync --all-extras
    @uv run pre-commit install
    @just lint

# Run linting on all files
lint:
    @uv run pre-commit run --all-files

# Run validator on awesome
validator:
    @uv run python scripts/validator.py

# Run test
test:
    @just lint
    @just validator

# Import projects - pass additional arguments to the importer script
import *args:
    @uv run scripts/importer.py {{args}}
