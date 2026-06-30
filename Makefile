PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
FRONTEND_DIR := frontend
HOST ?= 127.0.0.1
FRONTEND_PORT ?= 5173
BACKEND_PORT ?= auto
BACKEND_PORT_START ?= 8000
BROWSER_HOST ?= $(if $(filter 0.0.0.0,$(HOST)),localhost,$(HOST))

.PHONY: install install-backend install-frontend dev lint lint-backend lint-frontend test test-backend test-frontend

install: install-backend install-frontend

install-backend:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PIP) install -e ".[dev]"

install-frontend:
	cd $(FRONTEND_DIR) && npm ci

dev:
	@set -eu; \
	backend_port="$(BACKEND_PORT)"; \
	if [ "$$backend_port" = "auto" ]; then \
		backend_port="$$(HOST="$(HOST)" BACKEND_PORT_START="$(BACKEND_PORT_START)" $(PYTHON) -c 'import os; exec("""import socket\nhost = os.environ[\"HOST\"]\nstart = int(os.environ[\"BACKEND_PORT_START\"])\nfor port in range(start, start + 100):\n    with socket.socket() as sock:\n        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n        try:\n            sock.bind((host, port))\n        except OSError:\n            continue\n        print(port)\n        raise SystemExit(0)\nraise SystemExit(f\"No free backend port found in {start}-{start + 99}\")""")')"; \
	fi; \
	echo "Backend:  http://$(BROWSER_HOST):$$backend_port"; \
	echo "Frontend: http://$(BROWSER_HOST):$(FRONTEND_PORT)"; \
	$(VENV_PYTHON) manage.py migrate; \
	trap 'test -n "$${backend_pid:-}" && kill "$$backend_pid" 2>/dev/null || true; test -n "$${frontend_pid:-}" && kill "$$frontend_pid" 2>/dev/null || true' INT TERM EXIT; \
	$(VENV_PYTHON) manage.py runserver $(HOST):$$backend_port & \
	backend_pid=$$!; \
	cd $(FRONTEND_DIR); \
	VITE_API_BASE_URL=http://$(BROWSER_HOST):$$backend_port ./node_modules/.bin/vite --host $(HOST) --port $(FRONTEND_PORT) & \
	frontend_pid=$$!; \
	set +e; \
	wait -n $$backend_pid $$frontend_pid; \
	status=$$?; \
	set -e; \
	kill $$backend_pid $$frontend_pid 2>/dev/null || true; \
	wait $$backend_pid $$frontend_pid 2>/dev/null || true; \
	exit $$status

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
