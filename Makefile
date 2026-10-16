.DEFAULT_GOAL := help
.PHONY: help status log install install-be install-fe dev dev-be dev-fe \
        migrate makemigrations superuser seed shell test test-be test-fe coverage check celery-worker \
        lint lint-be lint-fe format build schema client up down clean

BACKEND  := backend
FRONTEND := frontend
VENV     := $(BACKEND)/.venv
PY       := $(VENV)/bin/python
PIP      := $(VENV)/bin/pip
MANAGE   := $(PY) $(BACKEND)/manage.py
PORT_BE  ?= 8000
PORT_FE  ?= 5173

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

# --- Git -------------------------------------------------------------------
status: ## Show git status
	@git status -sb

log: ## Show recent commits
	@git log --oneline --graph -15

# --- Setup -----------------------------------------------------------------
install: install-be install-fe ## Install backend + frontend dependencies

$(VENV)/bin/activate:
	python3 -m venv $(VENV)

install-be: $(VENV)/bin/activate ## Create venv and install backend deps
	$(PIP) install -U pip
	$(PIP) install -r $(BACKEND)/requirements/development.txt

install-fe: ## Install frontend deps
	cd $(FRONTEND) && npm install

# --- Run -------------------------------------------------------------------
dev: ## Run backend and frontend together (Ctrl+C stops both)
	@trap 'kill 0' INT TERM; \
	$(MAKE) --no-print-directory dev-be & \
	$(MAKE) --no-print-directory dev-fe & \
	wait

dev-be: ## Run Django dev server
	$(MANAGE) runserver 0.0.0.0:$(PORT_BE)

dev-fe: ## Run Vite dev server
	cd $(FRONTEND) && npm run dev -- --host --port $(PORT_FE)

# --- Django ----------------------------------------------------------------
migrate: ## Apply migrations
	$(MANAGE) migrate

makemigrations: ## Create migrations
	$(MANAGE) makemigrations

superuser: ## Create Django superuser
	$(MANAGE) createsuperuser

seed: ## Seed areas and compatibility rules
	$(MANAGE) seed_areas

shell: ## Django shell
	$(MANAGE) shell

# --- Quality ---------------------------------------------------------------
test: test-be test-fe ## Run all tests

test-be: ## Run backend tests (pytest)
	cd $(BACKEND) && .venv/bin/pytest

coverage: ## Backend tests with coverage report
	$(MAKE) -C $(BACKEND) coverage

check: ## Django check + migrations check
	$(MAKE) -C $(BACKEND) check

celery-worker: ## Run Celery worker (needs CELERY_ENABLED=True)
	$(MAKE) -C $(BACKEND) celery-worker

test-fe: ## Run frontend tests (vitest)
	cd $(FRONTEND) && npm run test -- --run

lint: lint-be lint-fe ## Lint everything

lint-be: ## Ruff check backend
	$(VENV)/bin/ruff check $(BACKEND)

lint-fe: ## Lint frontend
	cd $(FRONTEND) && npm run lint

format: ## Format backend (ruff) and frontend (prettier)
	$(VENV)/bin/ruff format $(BACKEND)
	cd $(FRONTEND) && npm run format

# --- API contract ----------------------------------------------------------
schema: ## Export OpenAPI schema from DRF (drf-spectacular)
	$(MANAGE) spectacular --file $(BACKEND)/openapi.yml --validate

client: schema ## Generate typed TS client from OpenAPI
	cd $(FRONTEND) && npx openapi-typescript ../$(BACKEND)/openapi.yml -o src/api/schema.d.ts

# --- Build / Docker --------------------------------------------------------
build: ## Build the Vue PWA
	cd $(FRONTEND) && npm run build

up: ## Start local docker stack (backend + postgres + redis)
	$(MAKE) -C $(BACKEND) docker-local

down: ## Stop local docker stack and remove volumes
	cd $(BACKEND) && docker compose -f docker/local/docker-compose.yml down -v

clean: ## Remove build artifacts and caches
	rm -rf $(FRONTEND)/dist $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache
	find $(BACKEND) -name __pycache__ -type d -prune -exec rm -rf {} +
