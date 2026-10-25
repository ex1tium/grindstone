# M1 backlog

The M1 tickets from section 7 of the accepted specifications (SPEC-01 to SPEC-10), ordered by dependency layer: a ticket starts once everything it depends on is merged. The specifications stay the source of each ticket's requirements, criteria and paths; this file tracks only state. Update a row in the pull request that changes its state.

**How a ticket is built in M1.** Grindstone cannot run its own tickets until M1 exists (M1-08 is the first), so a Claude Code session builds each one directly:

1. Branch `feat/tkt-nnnn-<slug>` from `main`; read the ticket's requirements, its acceptance criteria and the decisions they cite.
2. Write each acceptance criterion's named test, then the code, within the ticket's paths. A change outside them is named in the pull request with its reason.
3. Resolve any new dependency to its latest compatible release (ADR-46), pin it exactly and record it in `docs/m0/versions.md`.
4. `make check` passes; one squash-merged pull request per ticket, titled with the ticket ID. Mark the row `done` with the pull request number.

At most two tickets run at once, each in its own worktree, because tickets in a layer often share files (the contracts package's exports, `Makefile`, the CI workflow).

**States:** `todo` · `doing` · `review` (pull request open) · `done`.

**On the operator's machine:** TKT-0501 (secret ownership under Docker Desktop on WSL2, OQ-0501) and the live runs M1-01, M1-02 and M1-08, which act as the GitHub App.

## Layer 0

| Ticket | Spec | Work | Depends on | State | PR |
| --- | --- | --- | --- | --- | --- |
| TKT-0101 | [SPEC-01](../specs/SPEC-01-contracts-ids-hashing.md) | Contract base, typed IDs, references, provenance, run manifest | — | done | #16 |
| TKT-0201 | [SPEC-02](../specs/SPEC-02-store-runtime-lanes-blobs.md) | Database access, migrations runner, unit of work | — | done | #17 |

## Layer 1

| Ticket | Spec | Work | Depends on | State | PR |
| --- | --- | --- | --- | --- | --- |
| TKT-0102 | [SPEC-01](../specs/SPEC-01-contracts-ids-hashing.md) | Error envelope and kernel error codes | TKT-0101 | done | #20 |
| TKT-0103 | [SPEC-01](../specs/SPEC-01-contracts-ids-hashing.md) | Canonical form, semantic hash, `blob_set_version`, golden and refusal vectors in Python | TKT-0101 | done | #22 |
| TKT-0105 | [SPEC-01](../specs/SPEC-01-contracts-ids-hashing.md) | FF-03 schema compatibility check | TKT-0101 | done | #21 |
| TKT-0202 | [SPEC-02](../specs/SPEC-02-store-runtime-lanes-blobs.md) | DBOS in the lifespan, workflow registry and version check, start-up guard | TKT-0201 | todo | |
| TKT-0205 | [SPEC-02](../specs/SPEC-02-store-runtime-lanes-blobs.md) | Blob store and roots | TKT-0201 | todo | |
| TKT-0206 | [SPEC-02](../specs/SPEC-02-store-runtime-lanes-blobs.md) | FF-07 table ownership and FF-09 no stored derivations, with fixtures | TKT-0201 | todo | |
| TKT-0301 | [SPEC-03](../specs/SPEC-03-platform-registries-loader-configuration.md) | Registries, `core` names, manifest contracts, SDK 0.1.0 surface and contexts | TKT-0101 | review | #24 |

## Layer 2

| Ticket | Spec | Work | Depends on | State | PR |
| --- | --- | --- | --- | --- | --- |
| TKT-0104 | [SPEC-01](../specs/SPEC-01-contracts-ids-hashing.md) | TypeScript hashing against the golden vectors | TKT-0103 | todo | |
| TKT-0203 | [SPEC-02](../specs/SPEC-02-store-runtime-lanes-blobs.md) | External-step helper, kill points, crash harness, FF-10 | TKT-0202 | todo | |
| TKT-0204 | [SPEC-02](../specs/SPEC-02-store-runtime-lanes-blobs.md) | Lanes | TKT-0202 | todo | |
| TKT-0302 | [SPEC-03](../specs/SPEC-03-platform-registries-loader-configuration.md) | Loader in two phases, kinds as data, capability hashing, load-time rules including make and prove | TKT-0301 | todo | |
| TKT-0304 | [SPEC-03](../specs/SPEC-03-platform-registries-loader-configuration.md) | Event outbox, union, dispatcher | TKT-0202 | todo | |
| TKT-0607 | [SPEC-06-1](../specs/SPEC-06-1-stations-agent-host.md) | SDK ports `WorkspaceProvider` and `SubjectResolver`, their contracts and the kernel's `blob`, `blob_set` and `item_revision` resolvers | TKT-0301 | todo | |

## Layer 3

| Ticket | Spec | Work | Depends on | State | PR |
| --- | --- | --- | --- | --- | --- |
| TKT-0303 | [SPEC-03](../specs/SPEC-03-platform-registries-loader-configuration.md) | Instance and project configuration, secrets, `grindstone check` | TKT-0302, TKT-0201 | todo | |
| TKT-0401 | [SPEC-04](../specs/SPEC-04-items-changeset-decisions.md) | Items, revisions, edges, lifecycles, ID allocation, rendering, `core` kinds | TKT-0302, TKT-0201 | todo | |
| TKT-0402 | [SPEC-04](../specs/SPEC-04-items-changeset-decisions.md) | Decision records, kinds, answers, continuations | TKT-0304 | todo | |
| TKT-0901 | [SPEC-09](../specs/SPEC-09-sdlc-skeleton-factory.md) | Manifest: kinds, edges, lifecycles, capabilities, prompts, report schemas, template, configuration schema | TKT-0302 | todo | |
| TKT-1003 | [SPEC-10](../specs/SPEC-10-operator-surface.md) | Event streams | TKT-0304 | todo | |

## Layer 4

| Ticket | Spec | Work | Depends on | State | PR |
| --- | --- | --- | --- | --- | --- |
| TKT-0403 | [SPEC-04](../specs/SPEC-04-items-changeset-decisions.md) | Bundle import, ChangeDrafts, walk, rules, approval, apply | TKT-0401, TKT-0402 | todo | |
| TKT-0404 | [SPEC-04](../specs/SPEC-04-items-changeset-decisions.md) | SQL enum generation for kernel lifecycles | TKT-0401 | todo | |
| TKT-0405 | [SPEC-04](../specs/SPEC-04-items-changeset-decisions.md) | FF-08 single-writer check with fixtures | TKT-0401 | todo | |
| TKT-0501 | [SPEC-05](../specs/SPEC-05-deployment-users-secrets.md) | Images, users, entrypoints, compose (with the runner off every network), `make secrets` and `scripts/hash_password.py`, instance file | TKT-0303 | todo | |
| TKT-0602 | [SPEC-06-1](../specs/SPEC-06-1-stations-agent-host.md) | Stations: agent-user bindings, sessions, workspaces, host client, host event intake, reconciliation, activity registry, runner job dispatch | TKT-0204, TKT-0205, TKT-0303 | todo | |
| TKT-0801 | [SPEC-08](../specs/SPEC-08-check-station-evidence-delivery.md) | Evidence: plans with the task's current subject, records, freshness, gate, review recording, the `CheckMethod` port | TKT-0401, TKT-0302 | todo | |
| TKT-0905 | [SPEC-09](../specs/SPEC-09-sdlc-skeleton-factory.md) | Testbed bundle, toolchain image with pytest, testbed project configuration | TKT-0901 | todo | |

## Layer 5

| Ticket | Spec | Work | Depends on | State | PR |
| --- | --- | --- | --- | --- | --- |
| TKT-0406 | [SPEC-04](../specs/SPEC-04-items-changeset-decisions.md) | `change.draft_requested` contract and its consumer | TKT-0403, TKT-0304 | todo | |
| TKT-0502 | [SPEC-05](../specs/SPEC-05-deployment-users-secrets.md) | Workspace and session layout, and the host's helper that runs a command as an agent user (`spawnAsAgent` with umask 027 and a parent-death signal, `stopAll(user)`, which runs `kill -KILL -1` as that user and waits until `/proc` lists none of its processes, archive extraction, removal, session directories), which SPEC-06 part 1's host core uses | TKT-0501 | todo | |
| TKT-0503 | [SPEC-05](../specs/SPEC-05-deployment-users-secrets.md) | Claude preset launcher, security floor and credential self-test | TKT-0501 | todo | |
| TKT-0504 | [SPEC-05](../specs/SPEC-05-deployment-users-secrets.md) | People directory and viewer grants, tested on `createHost` from `@ahpd/sdk` with a stub backend, so it does not wait for SPEC-06's host core | TKT-0501 | todo | |
| TKT-0601 | [SPEC-06-2](../specs/SPEC-06-2-task-runs.md) | Task, run and turn lifecycles, reports, matching, templates, context pack, manifest with configuration hashes | TKT-0403, TKT-0302 | todo | |
| TKT-0802 | [SPEC-08](../specs/SPEC-08-check-station-evidence-delivery.md) | Mechanical checks: job building, dispatch, JUnit, interpretation | TKT-0801, TKT-0602 | todo | |
| TKT-0803 | [SPEC-08](../specs/SPEC-08-check-station-evidence-delivery.md) | Runner executors | TKT-0602 | todo | |
| TKT-0804 | [SPEC-08](../specs/SPEC-08-check-station-evidence-delivery.md) | Delivery port: prepare from events, decisions, modes at setup and before delivery, deliver, gate-state passes and posts, accept, observe, bypass reporting | TKT-0801, TKT-0403 | todo | |
| TKT-1001 | [SPEC-10](../specs/SPEC-10-operator-surface.md) | Login, sessions, CSRF, rate limit, error mapping, idempotency | TKT-0501, TKT-0201 | todo | |

## Layer 6

| Ticket | Spec | Work | Depends on | State | PR |
| --- | --- | --- | --- | --- | --- |
| TKT-0505 | [SPEC-05](../specs/SPEC-05-deployment-users-secrets.md) | FF-05, FF-06 and the M1-05 security tests in `make smoke` | TKT-0502, TKT-0503 | todo | |
| TKT-0603 | [SPEC-06-2](../specs/SPEC-06-2-task-runs.md) | Run and turn workflows: corrective prompt, suspend and resume, liveness, failure causes, permissions, collect, check tasks, delivery hand-over | TKT-0601, TKT-0602, TKT-0802, TKT-0406 | todo | |
| TKT-0605 | [SPEC-06-1](../specs/SPEC-06-1-stations-agent-host.md) | Agent host core: control API, backend wrapper, preset option mapping, ordered signed events | TKT-0502, TKT-0504 | todo | |
| TKT-0701 | [SPEC-07](../specs/SPEC-07-kernel-mcp-surface.md) | Server mount, token minting and verification, tool wrapper | TKT-0601, TKT-0501 | todo | |
| TKT-0904 | [SPEC-09](../specs/SPEC-09-sdlc-skeleton-factory.md) | GitHub adapter and a fake GitHub for tests | TKT-0804 | todo | |
| TKT-1002 | [SPEC-10](../specs/SPEC-10-operator-surface.md) | REST routes for projects, imports, items, ChangeSets, decisions, templates, commands, tasks, deliveries | TKT-1001, TKT-0403, TKT-0601, TKT-0804 | todo | |

## Layer 7

| Ticket | Spec | Work | Depends on | State | PR |
| --- | --- | --- | --- | --- | --- |
| TKT-0604 | [SPEC-06-1](../specs/SPEC-06-1-stations-agent-host.md) | Scripted preset | TKT-0605 | todo | |
| TKT-0606 | [SPEC-06-2](../specs/SPEC-06-2-task-runs.md) | Live run of the kernel's execution path with a real agent: a fixture capability on the Claude preset | TKT-0603, TKT-0503 | todo | |
| TKT-0702 | [SPEC-07](../specs/SPEC-07-kernel-mcp-surface.md) | The M1 tools and their contracts | TKT-0701, TKT-0603 | todo | |
| TKT-0902 | [SPEC-09](../specs/SPEC-09-sdlc-skeleton-factory.md) | Git workspaces: mirror, prepare, collect through the index with tiers and the diff as prover context, resolver | TKT-0901, TKT-0603 | todo | |
| TKT-1004 | [SPEC-10](../specs/SPEC-10-operator-surface.md) | OpenAPI document, drift and compatibility checks, generated client | TKT-1002 | todo | |

## Layer 8

| Ticket | Spec | Work | Depends on | State | PR |
| --- | --- | --- | --- | --- | --- |
| TKT-0703 | [SPEC-07](../specs/SPEC-07-kernel-mcp-surface.md) | Generated tool schemas, FF-02 and FF-03 extensions | TKT-0702 | todo | |
| TKT-0903 | [SPEC-09](../specs/SPEC-09-sdlc-skeleton-factory.md) | CI suite method | TKT-0902, TKT-0802 | todo | |
| TKT-0906 | [SPEC-09](../specs/SPEC-09-sdlc-skeleton-factory.md) | Live runs M1-01, M1-02 (both modes) and M1-08 on the operator's machine | TKT-0902, TKT-0905 | todo | |
| TKT-1005 | [SPEC-10](../specs/SPEC-10-operator-surface.md) | Web shell and its end-to-end tests | TKT-1004, TKT-1003 | todo | |
