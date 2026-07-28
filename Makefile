# ==============================================================================
# HIRON PLATFORM MAKEFILE
# ==============================================================================
# Standard task runner for developer commands across the monorepo.

.PHONY: help setup dev dev-build down lint format type-check test clean

help: ## Display available commands
	@echo "Hiron Platform Developer Task Runner"
	@echo "===================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Create local environment file from blueprint
	@if [ ! -f .env.local ]; then \
		cp .env.example .env.local; \
		echo "Created .env.local from .env.example"; \
	else \
		echo ".env.local already exists"; \
	fi

dev: ## Start local docker-compose environment
	docker compose up

dev-build: ## Rebuild and start local docker-compose environment
	docker compose up --build

down: ## Stop local docker-compose environment
	docker compose down --remove-orphans

lint: ## Run Python (Ruff) and Node (ESLint) linters
	@echo "Running Python Ruff linter..."
	uv run ruff check .
	@echo "Running Node ESLint linter..."
	pnpm lint

format: ## Run Python (Black) and Node (Prettier) code formatters
	@echo "Formatting Python code with Black..."
	uv run black .
	@echo "Formatting Frontend code with Prettier..."
	pnpm format:write

type-check: ## Run Python (MyPy strict) and TypeScript type checkers
	@echo "Type checking Python codebase with MyPy..."
	uv run mypy
	@echo "Type checking TypeScript codebase with tsc..."
	pnpm type-check

test: ## Run Python (Pytest) and Node (pnpm test) test suites
	@echo "Running Python test suite..."
	uv run pytest
	@echo "Running Frontend test suite..."
	pnpm test

clean: ## Clean local caches, temporary build artifacts, and coverage data
	@echo "Cleaning caches and build artifacts..."
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov .next dist build
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Clean completed."
