# Preferred local DX: native Postgres+Redis via scripts/dev-services.sh (not docker compose).
# Quality gates: lint · typecheck · test · secrets · check

.PHONY: services-up services-down services-status sync migrate seed api \
	lint typecheck test secrets check help

SRC := app
GITLEAKS_CONFIG := .gitleaks.toml
GITLEAKS_SOURCE := ..

# ── Runtime ───────────────────────────────────────────────────────────────────

services-up:
	./scripts/dev-services.sh up

services-down:
	./scripts/dev-services.sh down

services-status:
	./scripts/dev-services.sh status

sync:
	uv sync --extra dev

migrate:
	uv run alembic upgrade head

seed:
	uv run python -m app.seed.demo

api:
	uv run uvicorn app.main:app --reload --port 8000

# ── Quality gates ─────────────────────────────────────────────────────────────

lint:
	uv run pylint $(SRC)
	uv run pydoclint $(SRC)

typecheck:
	uv run mypy $(SRC)

test:
	uv run pytest

secrets:
	@command -v gitleaks >/dev/null 2>&1 || { \
		echo "gitleaks not found — install from https://github.com/gitleaks/gitleaks"; \
		exit 1; \
	}
	gitleaks detect --source $(GITLEAKS_SOURCE) --config $(GITLEAKS_CONFIG) --verbose --no-banner

check: typecheck lint test secrets
	@echo "All quality gates passed."

# ── Help ──────────────────────────────────────────────────────────────────────

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  services-up      Start local Postgres+Redis (.dev/)"
	@echo "  services-down    Stop local Postgres+Redis"
	@echo "  sync             uv sync --extra dev"
	@echo "  migrate          alembic upgrade head"
	@echo "  seed             load demo users/ideas"
	@echo "  api              uvicorn on :8000"
	@echo "  lint             pylint + pydoclint on $(SRC)"
	@echo "  typecheck        mypy on $(SRC)"
	@echo "  test             pytest -x --cov-fail-under=85 (critical paths)"
	@echo "  secrets          gitleaks detect (repo root; protects .env)"
	@echo "  check            typecheck + lint + test + secrets"
	@echo "  help             Show this message"
