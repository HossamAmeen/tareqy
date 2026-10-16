PY ?= .venv/bin/python
PIP ?= .venv/bin/pip

.PHONY: install install-dev run migrate makemigrations test coverage check lint format shell collectstatic celery-worker celery-beat test-rate-limit docker-local docker-staging docker-production deploy-staging deploy-production

install:
	$(PIP) install -r requirements/base.txt

install-dev:
	$(PIP) install -r requirements/development.txt

run:
	$(PY) manage.py runserver

migrate:
	$(PY) manage.py migrate

makemigrations:
	$(PY) manage.py makemigrations

test:
	$(PY) -m pytest

coverage:
	$(PY) -m pytest --cov=. --cov-report=term-missing

check:
	$(PY) manage.py check
	$(PY) manage.py makemigrations --check --dry-run

lint:
	.venv/bin/ruff check .

format:
	.venv/bin/ruff format .

shell:
	$(PY) manage.py shell

collectstatic:
	$(PY) manage.py collectstatic --noinput

celery-worker:
	.venv/bin/celery -A config worker --loglevel=INFO

celery-beat:
	.venv/bin/celery -A config beat --loglevel=INFO

test-rate-limit:
	$(PY) -m pytest -k "throttle or rate_limit"

docker-local:
	docker compose -f docker/local/docker-compose.yml up --build

docker-staging:
	docker compose --env-file .env -f docker/staging/docker-compose.yml up --build -d

docker-production:
	docker compose --env-file .env -f docker/production/docker-compose.yml up --build -d

deploy-staging:
	bash deploy/scripts/deploy.sh staging

deploy-production:
	bash deploy/scripts/deploy.sh production
