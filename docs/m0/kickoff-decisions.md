# M0 kickoff decisions

Answers from the operator on 17 October 2026 to the open questions in Foundation v4.1 and to the Step 1 scaffold choices. Choices that change the foundation are applied in Foundation v4.2 (ADR-37, ADR-38, ADR-39 and the open-questions table); the foundation is authoritative, and this file keeps the kickoff answers and the scaffold choices together in one place.

## Scope and governance

| Topic | Decision | Follow-up |
| --- | --- | --- |
| Q-11 MVP scope | Confirmed as recorded in ADR-36 | Close Q-11 in the foundation |
| License | Apache-2.0 | Add `LICENSE`; update README |
| Stable self-hosting instance (M1-08) | Decided at the M1 review; plain pull requests until then (ADR-33) | Revisit at M1 review |
| Foundation file | Editorial cleanup now as v4.2: drop the duplicate H1, caption the diagram placeholders, normalise ID formatting; apply the changes below in the same pass | v4.2 edit |

## Open questions

| ID | Decision | Differs from recorded default |
| --- | --- | --- |
| Q-1 | Vendored, patched ACP agent plugin | No |
| Q-2 | AHP 1.0, accepting 0.9 clients; VS Code attaches as a remote agent host with the token | No |
| Q-3 | Codex: SPK-3 tries subscription login headless; API key is the configuration-only fallback (mirrors Claude) | **Yes** |
| Q-4 | Codex sandbox mode through Codex's own configuration file, supplied by the capability | No |
| Q-5 | Skills are materialized into an agent-specific folder in the workspace before the session starts; `load_skill` returns skill bodies inline for any agent that cannot load workspace skills. Materialized skills are read-only to the agent and refused at copy-back (I-14) | **Yes** |
| Q-6 | FastMCP mounted in FastAPI, bearer token checked per request | No |
| Q-7 | Auto-merge waits for the branch update and a fresh status at the new head | No |
| Q-8 | Initial targets stand; reset at the M3 review from baselines | No |
| Q-9 | **Redesigned.** `ask` holds the call open until the consult finishes: MCP progress keepalives, client tool timeouts raised per capability, the answer cached durably so a dropped session re-asks and attaches to the in-flight or cached answer. A hard ceiling (seed 2 h, owned by SPEC-17) escalates to the operator. Park-and-resume remains only as fault recovery | **Yes**, needs ADR-37/38 |
| Q-10 | **Redesigned.** No numeric per-task or per-tree budgets. Runaway guards stay: depth ≤ 2, a live-children cap, a liveness (inactivity) timeout instead of total wall time, provider quota and rate-limit signals park the run. Cost is recorded and shown, never gating. One optional per-project spend/turn cap, off by default, for API-key runs | **Yes**, supersedes ADR-20 |

The Q-9 and Q-10 redesigns touch QG-5, QS-10, QS-11, I-17, ADR-14, ADR-20, ADR-24, the Task and Capability `budget` fields, the `budget_exhausted` cause, the `budget_overflow` decision and flag, the tripwire, M3-05, SPK-5 and the risks table. All of them are updated in the v4.2 edit.

## Step 1 scaffold and tooling

| Topic | Decision |
| --- | --- |
| Repository layout | uv workspace + pnpm workspace monorepo (below) |
| Python | Latest stable that DBOS, Pydantic, FastAPI, FastMCP and psycopg all support (3.15, else 3.14), exact patch pinned |
| Python lint and types | ruff (lint and format) + pyright strict |
| TypeScript lint and format | Biome; `svelte-check` for Svelte types |
| Base images | Official Debian slim images, pinned by digest |
| Git conventions | Conventional Commits, protected `main`, squash merge |
| Task runner | Makefile |
| Upgrades | Dependabot (pip/uv, npm, Docker, GitHub Actions) |
| GitHub test repository | New private `ex1tium/grindstone-testbed` with a ruleset and a GitHub App installation, created by the operator |
| Where work runs | Claude Code cloud sessions as much as possible (revised after kickoff); the SessionStart hook prepares each session. Agent and GitHub App credentials live in the cloud environment's settings while the App is installed on the testbed only |
| Specification review | A fresh session that wrote none of the specs reviews against the checklist, a different model family where available, then the operator approves |

```
grindstone/
├─ pyproject.toml                 # uv workspace root
├─ packages/grindstone/src/grindstone/
│   ├─ contracts/ store/ platform/
│   ├─ intent/ evidence/ decisions/ memory/ stations/
│   ├─ change/ work/ delivery/ surface/
│   └─ sdk/
├─ factories/sdlc/                # own pyproject, grindstone.factories entry point
├─ factories/notes/
├─ runner/                        # small Python job executor
├─ pnpm-workspace.yaml
├─ agent-host/                    # TypeScript on @ahpd/sdk
├─ web/                           # SvelteKit static
├─ packages/contracts-ts/         # generated from JSON Schema
├─ compose.yaml  Makefile  scripts/
├─ tests/  fixtures/
└─ docs/{foundation,specs,spikes,m0}
```
