# Grindstone — working rules for Claude sessions

Grindstone is a self-hosted orchestrator for agent-driven software development (see README.md). **Current state and next actions: `docs/m0/status.md` — read it first.**

## Authority
- `docs/foundation/grindstone-foundation.md` holds every commitment. When code or a spec disagrees with it, the foundation wins until a decision record changes it. Decision records are append-only: change one by adding a new ADR that supersedes or amends it, and update every tab that states the decision in the same edit, plus the revision history.
- Specifications follow the Planning playbook at the end of the foundation (template, ID blocks `REQ-nnxx`/`AC-nnxx-k`, validation checklist). A spec is reviewed by a session that did not write it, then the operator approves.
- A choice that crosses a module or factory boundary is proposed as a decision record, not decided inline.

## Commands
`make setup` · `make check` (lint, pyright strict, tests, fitness functions: what CI runs) · `make gen` (after changing `grindstone.contracts`) · `make up` / `make smoke` (Docker stack, M0-01) · `make help`.
Run `make check` before every push. `python -m scripts.ff.module_map > .importlinter` after changing the module map.

## Rules the fitness functions enforce
- FF-01: kernel modules import only what the module map allows; the kernel never imports `factories/`; factories import only `grindstone.sdk`; the runner is standard-library only and imports nothing of ours.
- FF-02: generated contracts must match the Pydantic source.
- FF-04: every dependency exact (`==`, exact semver), images by digest, actions by commit SHA.
- FF-13: every cited ID (I-, ADR-, QS-, M1-02, SPEC-, …) must exist in the foundation.

## Conventions
- Conventional Commits; squash-merged pull requests into `main`. No model identifiers in commits or code; the one exception is the operator's model choice in deployment configuration (`deploy/grindstone.toml`, `[agents.claude.models]`).
- Background agents only when the operator asks, at most one beside the lead session, and only in a different role (they use too much quota).
- Latest stable versions, pinned exactly, resolved from primary sources and recorded in `docs/m0/versions.md`.
- Secrets never go into the repository or chat. Cloud sessions read them from environment variables prefixed `GRINDSTONE_`; never print their values.

## Cloud sessions
`.claude/hooks/session-start.sh` installs Node and pnpm, syncs dependencies, starts Docker with a registry mirror and sets `COMPOSE_FILE` so images build through the session proxy. If the hook did not run (for example, on a branch not yet merged), run `CLAUDE_CODE_REMOTE=true CLAUDE_ENV_FILE=/tmp/gs.env .claude/hooks/session-start.sh && source /tmp/gs.env`.
