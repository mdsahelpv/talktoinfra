.PHONY: dev lint test clean setup

# ── Setup ─────────────────────────────────────────────────────────────
setup:
	pip install -e ./shared
	pip install -e ./orchestrator
	pip install -e ./agent
	pip install -e ./cli
	@echo "✅ All packages installed"

setup-dev: setup
	cd web && npm install
	@echo "✅ Dev setup complete"

# ── Development ────────────────────────────────────────────────────────
dev:
	docker compose up --build -d
	@echo "✅ Orchestrator: http://localhost:8000"
	@echo "✅ Web UI: http://localhost:5173"

dev-logs:
	docker compose logs -f

dev-stop:
	docker compose down

dev-clean:
	docker compose down -v

# ── Individual Services ────────────────────────────────────────────────
orchestrator-dev:
	cd orchestrator && uvicorn src.main:app --reload --port 8000

agent-dev:
	cd agent && python -m src.main

cli-dev:
	talktoinfra chat

web-dev:
	cd web && npm run dev

# ── Quality ────────────────────────────────────────────────────────────
lint:
	cd orchestrator && ruff check src/ && ruff format --check src/
	cd agent && ruff check src/ && ruff format --check src/
	cd cli && ruff check src/ && ruff format --check src/

typecheck:
	cd orchestrator && mypy src/ || true
	cd agent && mypy src/ || true
	cd cli && mypy src/ || true

test:
	cd orchestrator && pytest -v
	cd agent && pytest -v
	cd cli && pytest -v

# ── Clean ──────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	rm -rf web/dist
	@echo "✅ Cleaned"

# ── Docker ─────────────────────────────────────────────────────────────
docker-build:
	docker compose build

# ── Help ───────────────────────────────────────────────────────────────
help:
	@echo "TalkToInfra — Development Commands"
	@echo ""
	@echo "  make setup         Install all Python packages (editable)"
	@echo "  make setup-dev     Full dev setup (Python + npm)"
	@echo "  make dev           Start full stack with Docker Compose"
	@echo "  make lint          Run ruff linter on all packages"
	@echo "  make test          Run all Python tests"
	@echo "  make clean         Remove cache files"
	@echo ""
	@echo "Individual:"
	@echo "  make orchestrator-dev   Run orchestrator (uvicorn --reload)"
	@echo "  make agent-dev          Run agent"
	@echo "  make cli-dev            Start CLI chat"
	@echo "  make web-dev            Run web dev server (Vite)"
