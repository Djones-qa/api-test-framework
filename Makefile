.PHONY: help install dev test test-contract test-integration test-data test-perf \
        test-all coverage lint format clean docker-up docker-down

PYTHON  := python
PYTEST  := pytest
REPORTS := reports

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────────────

install:  ## Install production dependencies
	pip install -r requirements.txt

dev:  ## Install all dependencies (including dev)
	pip install -r requirements.txt -r requirements-dev.txt
	cp -n .env.example .env || true

# ── Running the API ───────────────────────────────────────────────────────────

run:  ## Start the API server (development mode)
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ── Testing ───────────────────────────────────────────────────────────────────

test-contract:  ## Run contract tests only
	$(PYTEST) tests/contract/ -v --tb=short

test-integration:  ## Run integration tests only
	$(PYTEST) tests/integration/ -v --tb=short

test-data:  ## Run data-driven tests only
	$(PYTEST) tests/data_driven/ -v --tb=short

test-perf:  ## Run performance tests only
	$(PYTEST) tests/performance/ -v -s --tb=short

test:  ## Run all tests (excluding performance)
	$(PYTEST) tests/contract/ tests/integration/ tests/data_driven/ -v --tb=short

test-all:  ## Run ALL tests including performance
	$(PYTEST) tests/ -v --tb=short

# ── Coverage ──────────────────────────────────────────────────────────────────

coverage:  ## Run tests with coverage report
	$(PYTEST) tests/contract/ tests/integration/ tests/data_driven/ \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:$(REPORTS)/htmlcov \
		--cov-fail-under=80

# ── Reports ───────────────────────────────────────────────────────────────────

report:  ## Run tests and generate HTML report
	mkdir -p $(REPORTS)
	$(PYTEST) tests/ \
		--html=$(REPORTS)/test_report.html \
		--self-contained-html \
		-v

# ── Lint & format ─────────────────────────────────────────────────────────────

lint:  ## Run ruff linter
	ruff check .

format:  ## Auto-format code with ruff
	ruff format .

typecheck:  ## Run mypy type checker
	mypy app/ --ignore-missing-imports

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up:  ## Start API via docker-compose
	docker-compose up --build -d api

docker-down:  ## Stop docker-compose services
	docker-compose down

docker-test:  ## Run tests inside Docker
	docker-compose run --rm test

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:  ## Remove generated files and databases
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -f *.db test_*.db
	rm -rf $(REPORTS) htmlcov .coverage .pytest_cache
