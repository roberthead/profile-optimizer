.PHONY: help validate validate-backend validate-frontend \
       lint-backend test-backend lint-frontend typecheck-frontend test-frontend

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Aggregate ────────────────────────────────────────────────

validate: validate-backend validate-frontend ## Run all checks (lint, typecheck, test)

validate-backend: lint-backend test-backend ## Run all backend checks

validate-frontend: lint-frontend typecheck-frontend test-frontend ## Run all frontend checks

VENV := backend/venv/bin

# ── Backend ──────────────────────────────────────────────────

lint-backend: ## Run ruff linter and formatter check
	cd backend && $(CURDIR)/$(VENV)/ruff check . && $(CURDIR)/$(VENV)/ruff format --check .

test-backend: ## Run backend pytest suite
	cd backend && $(CURDIR)/$(VENV)/python -m pytest

# ── Frontend ─────────────────────────────────────────────────

lint-frontend: ## Run ESLint
	cd frontend && npm run lint

typecheck-frontend: ## Run TypeScript type checking
	cd frontend && npx tsc -b --noEmit

test-frontend: ## Run frontend tests
	@echo "No frontend tests configured yet -- skipping"
