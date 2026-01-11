# MichelangeloCC Makefile
#
# Common development and installation tasks
#

.PHONY: help install install-dev install-uv uninstall venv test test-cov test-cov-check lint typecheck check clean clean-all

# Configuration
PYTHON := python3
VENV := .venv
BIN := $(VENV)/bin

# Default target
help:
	@echo "MichelangeloCC Development Commands"
	@echo ""
	@echo "Installation:"
	@echo "  make install       Install globally via pipx (recommended for users)"
	@echo "  make install-uv    Install globally via uv"
	@echo "  make install-dev   Install in development mode with venv"
	@echo "  make uninstall     Uninstall from pipx"
	@echo ""
	@echo "Development:"
	@echo "  make venv          Create virtual environment"
	@echo "  make test          Run tests"
	@echo "  make test-cov      Run tests with coverage report"
	@echo "  make test-cov-check  Run tests and fail if coverage < 80%"
	@echo "  make lint          Run linting (ruff)"
	@echo "  make typecheck     Run type checking (mypy)"
	@echo "  make check         Run all checks (lint + typecheck + test)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         Remove build artifacts"
	@echo "  make clean-all     Remove build artifacts and venv"

# Check Python version >= 3.10
check-python:
	@$(PYTHON) -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null \
		|| (echo "Error: Python 3.10+ required. Found: $$($(PYTHON) --version 2>&1)"; exit 1)

# Create virtual environment
venv: check-python
	@if [ ! -d $(VENV) ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
		echo "Virtual environment created at $(VENV)"; \
	else \
		echo "Virtual environment already exists at $(VENV)"; \
	fi

# Install for development (editable mode with dev dependencies)
install-dev: venv
	@echo "Installing in development mode..."
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"
	@echo ""
	@echo "Installation complete!"
	@echo ""
	@echo "Activate the virtual environment with:"
	@echo "  source $(VENV)/bin/activate"
	@echo ""
	@echo "Then you can run:"
	@echo "  mcc --help"

# Install globally via pipx (for users)
install:
	@if command -v pipx >/dev/null 2>&1; then \
		echo "Installing via pipx..."; \
		pipx install --force .; \
	else \
		echo "Error: pipx not found. Install it first:"; \
		echo "  brew install pipx  # macOS"; \
		echo "  apt install pipx   # Ubuntu/Debian"; \
		exit 1; \
	fi

# Install globally via uv
install-uv:
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing via uv..."; \
		uv tool install --force .; \
	else \
		echo "Error: uv not found. Install it first:"; \
		echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		exit 1; \
	fi

# Uninstall from pipx
uninstall:
	@if command -v pipx >/dev/null 2>&1; then \
		pipx uninstall michelangelocc || true; \
	fi
	@if command -v uv >/dev/null 2>&1; then \
		uv tool uninstall michelangelocc || true; \
	fi
	@echo "Uninstalled"

# Run tests
test: venv
	@if [ -d "tests" ]; then \
		$(BIN)/pytest tests/ -v; \
	else \
		echo "No tests directory found"; \
	fi

# Run tests with coverage report
test-cov: venv
	$(BIN)/pytest tests/ -v --cov=michelangelocc --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "HTML coverage report: htmlcov/index.html"

# Run tests and fail if coverage < 80%
test-cov-check: venv
	$(BIN)/pytest tests/ --cov=michelangelocc --cov-fail-under=80

# Run linting
lint: venv
	$(BIN)/pip install -q ruff
	$(BIN)/ruff check src/

# Run type checking
typecheck: venv
	$(BIN)/pip install -q mypy
	$(BIN)/mypy src/ --ignore-missing-imports

# Run all checks
check: lint typecheck test

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Clean everything including venv
clean-all: clean
	rm -rf $(VENV)
	@echo "Cleaned all build artifacts and virtual environment"
