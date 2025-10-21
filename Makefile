# Makefile for Insight Graph development

.PHONY: help install test lint format clean docker-build docker-up docker-down

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-asyncio black ruff mypy

test:  ## Run tests
	pytest --cov=insight_graph --cov-report=term-missing

test-fast:  ## Run tests without coverage
	pytest -x

lint:  ## Run linters
	ruff check insight_graph/
	black --check insight_graph/
	mypy insight_graph/ --ignore-missing-imports

format:  ## Format code
	black insight_graph/ tests/
	ruff check --fix insight_graph/

clean:  ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type f -name '.coverage' -delete
	rm -rf htmlcov/ .pytest_cache/

demo:  ## Initialize demo data
	python scripts/init_demo_data.py

docker-build:  ## Build Docker image
	docker build -t insight-graph:latest .

docker-up:  ## Start services with docker-compose
	docker-compose up -d

docker-down:  ## Stop services
	docker-compose down

docker-logs:  ## View logs
	docker-compose logs -f

backup:  ## Run backup
	./scripts/backup.sh

metrics:  ## Start Prometheus metrics exporter
	python -m insight_graph.monitoring.exporter

cli:  ## Open CLI
	python -m insight_graph

api:  ## Start API server
	python -m uvicorn insight_graph.api.server:app --reload

discord-bot:  ## Start Discord bot
	python -m insight_graph.ingest.discord_bot

brief:  ## Generate daily brief
	python -m insight_graph.briefs.daily

watch-tests:  ## Watch and run tests on file changes
	pytest-watch

release:  ## Create a new release (requires VERSION)
	@if [ -z "$(VERSION)" ]; then echo "Usage: make release VERSION=0.2.0"; exit 1; fi
	@echo "Creating release $(VERSION)"
	@sed -i 's/version = "[^"]*"/version = "$(VERSION)"/' pyproject.toml
	@git add pyproject.toml CHANGELOG.md
	@git commit -m "chore: bump version to $(VERSION)"
	@git tag -a v$(VERSION) -m "Release version $(VERSION)"
	@echo "Release created. Push with: git push origin main --tags"
