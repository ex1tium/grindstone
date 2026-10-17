# Grindstone

**Make agent-driven work trustworthy enough to delegate.**

Grindstone is a self-hosted orchestrator for agent-driven software development with a person in the loop. You state intent; agents do the work; Grindstone keeps the intent typed and versioned, proves every result independently against the exact intent it claims to satisfy, feeds discoveries back into the specification, and asks you only what only a person should decide.

> **Status: pre-M0.** This repository holds the foundation documents and, soon, the scaffold. Nothing here runs yet. Single operator, self-hosted, GitHub only.

## The idea

Every factory runs the same five beats. The kernel owns the beats; the factory names them.

| Beat | Kernel concept | Software development (MVP) |
| --- | --- | --- |
| State intent | Item, ChangeSet, Decision | Product, features, specifications, requirements, criteria, tickets |
| Do the work | Task (with consult and delegate) | Coding agents in isolated worktrees, calling security or test specialists |
| Prove it | Check, by someone other than the maker | CI suite on a credential-less runner, plus test, code and security reviewers |
| Learn and change | ChangeSet from findings and learnings | Findings amend the specification through a reviewed change |
| Deliver | Decision, then a delivery adapter | Pull request that can merge only on fresh, independent evidence |

Three properties carry the design:

| Property | Means |
| --- | --- |
| Typed, versioned intent | Everything agreed on is an item with a stable ID and content hash. It changes only through a ChangeSet whose full impact was reviewed first. |
| Independent, fresh proof | Work is done only when someone other than its maker has proven it against the exact inputs, subject and environment. Evidence goes stale on its own when any of those change. |
| Bounded, recorded authority | People answer typed decisions with a recommendation in front of them. Policy answers only what you allowed, and every answer can be reverted. |

## Architecture in brief

A modular monolith with a domain-neutral **kernel** and plug-in **factories**. Software development (`sdlc`) is the first factory and the reason Grindstone exists; a code-free `notes` fixture proves the kernel is neutral. Reverse engineering, testing, CAD, PCB and game development are sketched, not planned.

| Container | Role |
| --- | --- |
| `grindstone` | Kernel, factories, DBOS workflows, REST API and static UI, kernel MCP server, delivery adapters. Holds all authority and credentials. |
| `agent-host` | Thin AHP host on `@ahpd/sdk`; runs Claude Code, then Codex, over ACP. Holds model credentials only. |
| `runner` | Runs mechanical checks on a materialized subject, one job at a time, with no credentials. |
| `postgres` | The only store of records. |

Agents propose; the kernel applies. They reach Grindstone only through a per-task MCP surface, never deliver, and never change the configuration that governs them.

## Software development loop

`/init` → `/discover` → `/plan` → `/implement` → pull request, with `/patch` for small changes and `/repair` for stale or failing evidence. Specification and code move together: every ticket implements requirements by typed reference, every acceptance criterion names its requirement and verification method, and every commit is proven against the exact revisions it was built from.

## Roadmap

| Milestone | Outcome |
| --- | --- |
| M0 Foundations | Repository, CI, four empty services; spikes SPK-1 to SPK-5 settled |
| M1 Walking skeleton | A hand-written ticket becomes a verified pull request; Grindstone starts building itself |
| M2 Traceable intent | Full item model and relation graph; freshness computed; kernel proven neutral |
| M3 Safe change and cooperation | Findings flow back through reviewed ChangeSets; consult and delegate |
| M4 Discovery and planning | Idea to approved tickets, decided in the browser |
| M5 MVP | Memory, outer loop, autonomy L2, operations |

After the MVP: R1 factories as packages and static reverse engineering, R2 snapshot and restore, semantic search and L3, R3 microVM stations, R4 full-VM stations and hardware.

## Quality bars

Correctness, traceability, freshness (computed, never stored), durability (idempotent, resumable workflows), type safety (Pydantic is the single source of types), reversibility, independence (nothing proves its own work) and simplicity (the fewest moving parts).

## Development

Dependencies are the latest stable releases, pinned exactly; images are pinned by digest; versions are resolved at M0 from primary sources. Python is managed with uv, Node packages with pnpm. Cloud development environment setup lives in `scripts/` once added.

## Contributing

Specification before code. Each spec cites the invariants and decisions it implements and maps every exit criterion it delivers to acceptance criteria tied to tests. A choice that crosses a module or factory boundary is proposed as a decision record, not decided inline. See the planning playbook in the foundation.

## License

Not yet chosen. Private repository; all rights reserved until decided.