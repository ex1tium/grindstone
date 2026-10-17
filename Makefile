# Common commands. Python runs through uv, TypeScript through pnpm.
# `make check` is what CI runs; run it before pushing.

.DEFAULT_GOAL := help
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

UV := uv run --locked
PNPM := pnpm

.PHONY: help
help: ## List targets
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

.PHONY: setup
setup: ## Install the locked Python and Node toolchains
	uv sync --locked
	$(PNPM) install --frozen-lockfile

.PHONY: fmt
fmt: ## Format Python and TypeScript
	$(UV) ruff format .
	$(UV) ruff check --fix .
	$(PNPM) exec biome check --write .

.PHONY: lint
lint: ## Lint Python and TypeScript
	$(UV) ruff format --check .
	$(UV) ruff check .
	$(PNPM) exec biome ci .

.PHONY: typecheck
typecheck: ## Type-check Python (pyright strict) and TypeScript
	$(PNPM) exec pyright
	$(PNPM) -r typecheck

.PHONY: test
test: ## Run Python and TypeScript tests
	$(UV) pytest
	$(PNPM) -r --if-present test

.PHONY: gen
gen: ## Regenerate JSON Schemas and TypeScript from the Pydantic contracts
	$(UV) python scripts/gen_contract_schemas.py
	node scripts/gen-contracts-ts.mjs
	$(PNPM) exec biome format --write packages/contracts-ts > /dev/null

.PHONY: ff
ff: ## Run the M0 fitness functions (FF-01, FF-02, FF-04, FF-13)
	$(UV) lint-imports
	$(MAKE) --no-print-directory gen
	git diff --exit-code -- packages/contracts-ts || { echo "FF-02 generated contracts drifted: run make gen and commit"; exit 1; }
	$(UV) python -m scripts.ff.pins
	uv lock --check
	$(UV) python -m scripts.ff.traceability

.PHONY: check
check: lint typecheck test ff ## Everything CI runs, except the compose smoke test

.PHONY: secrets
secrets: ## Create local development secrets under secrets/ (never commit them)
	scripts/dev-secrets.sh

.PHONY: up
up: secrets ## Build and start the stack, waiting until every service is healthy
	docker compose up --build --wait --wait-timeout 180

.PHONY: down
down: ## Stop the stack (volumes are kept)
	docker compose down

.PHONY: smoke
smoke: up ## M0-01: start the stack, verify health and mounts, stop it
	uv run --locked python scripts/compose_smoke.py
	docker compose down
