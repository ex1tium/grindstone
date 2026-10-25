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
ff: ## Run the fitness functions (FF-01..04, FF-10, FF-13) and the workflow-version check; FF03_BASE=ref sets their base
	$(UV) lint-imports
	$(MAKE) --no-print-directory gen
	git diff --exit-code -- packages/contracts-ts || { echo "FF-02 generated contracts drifted: run make gen and commit"; exit 1; }
	$(UV) python -m scripts.ff.schema_compat $(if $(FF03_BASE),--base $(FF03_BASE))
	$(UV) python -m scripts.ff.workflow_versions $(if $(FF03_BASE),--base $(FF03_BASE))
	$(UV) python -m scripts.ff.idempotency
	$(UV) python -m scripts.ff.pins
	uv lock --check
	$(UV) python -m scripts.ff.traceability

.PHONY: check
check: lint typecheck test ff ## Everything CI runs, except the compose smoke test

.PHONY: secrets
secrets: ## Create every deployment secret under secrets/, 0600, never overwriting one (never commit them)
	bash scripts/make_secrets.sh

.PHONY: up
up: secrets ## Build and start the stack, waiting until every service is healthy
	docker compose up --build --wait --wait-timeout 180

.PHONY: down
down: ## Stop the stack (volumes are kept)
	docker compose down

.PHONY: smoke
smoke: up ## M0-01 and SPEC-05: start the stack, verify health, mounts and the security tests, stop it
	uv run --locked python scripts/compose_smoke.py
	GRINDSTONE_COMPOSE_STACK=1 uv run --locked pytest tests/deployment/test_stack.py
	docker compose down

FIXTURE ?= ../grindstone-testbed

.PHONY: fixture
fixture: ## M0-04: the fixture project's tagged tests pass in the runner image (FIXTURE=checkout)
	$(UV) python scripts/fixture_check.py $(FIXTURE)

.PHONY: benchmark
benchmark: ## M0-04: generate the 20,000-item benchmark project into build/benchmark
	rm -rf build/benchmark
	$(UV) python -m scripts.benchmark build/benchmark > /dev/null
	@cat build/benchmark/manifest.json
