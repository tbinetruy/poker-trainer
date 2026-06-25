PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
FRONTEND_DIR := frontend

.PHONY: install install-backend install-frontend lint lint-backend lint-frontend test test-backend test-frontend

install: install-backend install-frontend

install-backend:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PIP) install -e ".[dev]"

install-frontend:
	cd $(FRONTEND_DIR) && npm ci

lint: lint-backend lint-frontend

lint-backend:
	$(VENV_PYTHON) -m ruff check .

lint-frontend:
	cd $(FRONTEND_DIR) && npm run lint

test: test-backend test-frontend

test-backend:
	$(VENV_PYTHON) -m pytest

test-frontend:
	cd $(FRONTEND_DIR) && if npm run | grep -qE '^  test$$'; then npm test; else echo "No frontend test script configured; skipping."; fi
