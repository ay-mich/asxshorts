# Makefile for asxshorts package development
.PHONY: help install deps test lint format security pre-commit build clean ci

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Dependencies
install: ## Install dev dependencies
	uv sync --extra dev

deps: ## Export production dependencies to requirements.txt
	uv export --format requirements-txt --no-dev --output-file requirements.txt

deps-dev: ## Export dev dependencies to requirements-dev.txt
	uv export --format requirements-txt --extra dev --output-file requirements-dev.txt

# Testing
test: ## Run tests with coverage
	uv run pytest

# Code quality
format: ## Format and fix code with ruff
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

lint: ## Check code with ruff
	uv run ruff check src/ tests/

type-check: ## Run mypy type checking
	uv run mypy src/

# Security
security: ## Run security scans
	uv run bandit -r src/
	uv run pip-audit --ignore-vuln GHSA-4xh5-x5gv-qwph

# Pre-commit
pre-commit: ## Install and run pre-commit
	uv run pre-commit install
	uv run pre-commit run --all-files

# Build
build: ## Build the package
	uv build

# Clean
clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ htmlcov/ .mypy_cache/ .ruff_cache/

# CI
ci: deps deps-dev lint type-check security test build ## Run full CI pipeline
