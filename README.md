# Grindstone

**Make agent-driven work trustworthy enough to delegate, in any domain, from one decision to an entire build.**

Grindstone is a self-hosted orchestrator for agent work with a person in the loop. You state intent; agents do the work; Grindstone keeps the intent typed and versioned, proves every result independently against the exact intent it claims to satisfy, feeds what the work discovers back into the intent, and asks you only what only a person should decide. You choose how much to delegate: work alongside agents, hand them tickets, or, after the MVP, let an orchestrator drive a whole build from a one-shot idea under a charter you set.

It is built as a small **domain-neutral kernel** with plug-in **factories**. The kernel holds the guarantees: provenance, freshness, independent proof, reviewed change, typed decisions, and durable, bounded execution. A factory teaches it one domain. Software development is the first factory and the reason Grindstone exists. Reverse engineering, testing and security, CAD, PCB, game development and in-house domains are meant to follow on the same kernel, with no change to it.

> **Status: M1, walking skeleton.** M0 closed on 19 October 2026 ([review](docs/m0/review.md)): the repository scaffold, CI with the M0 fitness functions, the four-container stack and the GitHub testbed are in place, and spikes SPK-1, SPK-2, SPK-4 and SPK-5 have filed their reports. Foundation v4.9 is accepted, and the ten M1 specifications are accepted; their tickets are being built. Foundation v4.10 (ADR-48 to ADR-53: agent accounts, the delivery queue, people as makers, principals, the orchestrator and routine delivery) is proposed and awaits the operator's acceptance. Grindstone is for a single operator, self-hosted, with GitHub only for now. The live handover is [`docs/m0/status.md`](docs/m0/status.md).

## Why

Agent-driven work goes wrong in the same ways in every domain:

- **Intent is lost.** Requirements live in prompts and chat history. Nothing records which version a result was built against.
- **Agents grade their own work.** "Done" means an agent said so. No independent evidence is tied to the exact intent and subject (a commit, a binary, a model or a board).
- **Discoveries don't flow back.** Gaps are fixed locally and forgotten, and the next agent repeats the mistake.
- **Change is unsafe.** Changing a requirement or an interface gives no view of what it affects, or of which evidence it invalidates.
- **Supervision does not scale.** You either babysit every session or review large outputs with no trace back to intent.

Grindstone solves these once, in the kernel, so every domain gets the same answer.

| Property | Means |
| --- | --- |
| Typed, versioned intent | Everything agreed on is an item with a stable ID and a content hash. It changes only through a ChangeSet whose full impact was reviewed first. |
| Independent, fresh proof | Work is done only when someone other than its maker has proven it against the exact inputs, subject and environment. Evidence goes stale on its own when any of those change. |
| Bounded, recorded authority | People answer typed decisions with a recommendation in front of them. Policy, and after the MVP an orchestrator under your charter, answers only what you granted, and every answer can be reverted. |

## The kernel

The kernel is a grammar of three nouns and four verbs (ADR-07). It sits on a substrate of a content-addressed blob store, versioned subjects, a delivery port and interface items. It ships with no domain of its own.

| Concept | Kind | One line |
| --- | --- | --- |
| Item | noun | A typed, hashed, versioned unit of intent or knowledge |
| Capability | noun | A specialist defined as data: prompt, agent, skills, toolbox, what it produces and offers |
| Station | noun | Where work or proof runs, with an isolation tier from T0 (read-only) to T3 (full VM or hardware) |
| Task | verb | One unit of work with pinned inputs, an output contract, a check plan and limits |
| Check | verb | Evidence produced by someone other than the maker, bound to exact inputs, subject and environment |
| ChangeSet | verb | The only way intent changes: impact reviewed to a fixed point, then applied atomically |
| Decision | verb | Authority: a person, or a policy the person approved, answers a typed question |

Three rules keep the grammar safe:

1. **Make and prove are separate.** A check is run by a different capability, in a different task run, on a workspace the maker never wrote. Mechanical checks run on a station with no credentials.
2. **Agents never talk to each other.** They cooperate only by loading a skill, consulting a specialist or delegating to one. All of this goes through the kernel and is recorded.
3. **Results travel as pinned references.** Items and files cross task and factory boundaries by revision and hash, never as copied conversation. When the source changes, everything built on it goes stale.

The division of labour follows from these rules. You decide intent, agents propose, the kernel applies, and only independent evidence closes work. You may make work too: take over a stuck run or submit your own commit, and it is proven by the same pipeline (ADR-50).

## Delegation modes

After the MVP one orchestrator per project, a capability the kernel ships that drives commands and decisions the way an engineer would and never writes or reviews code itself, works under a charter you write; each factory teaches it its domain through a playbook, and a factory's part of a project can get a narrower sub-charter. A charter states the mode, the decisions it may answer, the checkpoints where it must ask, and its limits (ADR-52).

| Mode | The orchestrator | You | From |
| --- | --- | --- | --- |
| Assist | Drives the work, retries and triages, and recommends every other answer | Answer every other decision | R2 |
| Checkpointed | Also answers granted decisions within approved scope | Answer at the checkpoints you chose, and everything flagged | R2 |
| Autonomous | Answers every granted decision; a question it would have asked becomes a recorded assumption | Review the assumptions and the build report | R5 |

When an agent asks a question, the orchestrator studies a snapshot of that agent's workspace, picks the best option, adjusts it or proposes a better way, and cites its evidence. Anything that changes intent still goes through a reviewed ChangeSet, and overturning an assumption later is an ordinary change.

## Factories

A factory packages one domain as a manifest of seven parts (ADR-21):

| Part | Declares | Software development | Reverse engineering |
| --- | --- | --- | --- |
| Item kinds | Kinds, fields, relations, lifecycles | Requirement, criterion, ticket, specification | Target, function, claim, report |
| Task templates | Bounded workflows exposed as commands | `/discover`, `/plan`, `/implement` | `/triage`, `/analyse`, `/confirm` |
| Capabilities | Specialists | Implementer, spec author, auditor, reviewers | Static analyst, finding writer |
| Check methods | How results are proven | CI suite on the check station | Reproduction, cross-tool agreement |
| Subjects and workspaces | What is proven and where it is made | Git commits in worktrees | Binaries as blobs |
| Delivery adapters | How verified results leave | GitHub pull request | Report export |
| Interface shapes | Contracts with other factories | Provides `api_contract` | Provides `format_spec` |

A factory is mostly data: YAML manifests, Markdown prompts and skills, and JSON Schemas. Code is allowed only for adapters and check methods, and a factory with no code at all is valid. Every factory passes a conformance kit. A factory cannot add a verb, bypass a ChangeSet, mark its own output verified, hand an agent delivery credentials, or read another factory's private items. Anything the grammar cannot express is a kernel change, made through a decision record.

Every factory runs the same loop; the kernel owns the beats and the factory names them:

| Beat | Kernel concept | Software development | Reverse engineering |
| --- | --- | --- | --- |
| State intent | Item, ChangeSet, Decision | Product, features, specifications, tickets | Target, questions, scope of analysis |
| Do the work | Task, with consult and delegate | Implementer in a worktree, consulting a security specialist | Static analyst driving Ghidra, delegating a parser to SDLC |
| Prove it | Check, by someone other than the maker | CI suite, test, code and security reviewers | Reproduction on the pinned binary, a second tool, a reviewer |
| Learn and change | ChangeSet from findings | Findings amend the specification | Findings revise the report and interfaces |
| Deliver | Decision, then a delivery adapter | Pull request and merge | Report export, interface published |

**Factories working together.** Several factories can share one project, with one item graph, one decision queue and one evidence store. They connect only through `core.interface` items: typed contracts with a provider and consumers, such as a file format, an API, a pinout or a mechanical envelope. Each side proves its half. A change to an interface goes through one ChangeSet whose impact reaches both sides.

| Factory | Status |
| --- | --- |
| `sdlc`: software development | MVP, built from M1 |
| `notes`: code-free fixture | MVP, test only. It proves the kernel is domain-neutral (M2-05) |
| `re`: static reverse engineering | First release after the MVP (R1) |
| `qa`, `cad`, `pcb`, `game` | Sketched to test the kernel boundary, not planned |

Computer use and hardware are the long-term direction. They arrive as new station tiers and capabilities, not as a new core.

## The first factory: software development

The `sdlc` factory runs an agent-driven software development loop (ASDLC). It takes a repository from an idea to merged pull requests and keeps the specification and the code moving together.

| Command | Does |
| --- | --- |
| `/init` | Drafts principles, conventions and project configuration |
| `/discover` | Interviews you and drafts the product, features and milestones |
| `/plan` | Writes specifications with an independent auditor, then breaks them into tickets |
| `/implement` | Runs coding agents in isolated worktrees, proves each commit, and opens a pull request carrying its evidence |
| `/patch` | Takes a small change of intent through to tickets |
| `/repair` | Fixes stale or failing evidence |

Every ticket implements requirements by typed reference. Every acceptance criterion names its requirement and how it is verified. A pull request can merge only when fresh, independent evidence shows that every criterion holds at that exact commit. When implementation finds a gap, the finding amends the specification through a reviewed ChangeSet, so the fix does not stay in the chat.

## Architecture

The architecture is a Python modular monolith with import-enforced boundaries. It runs durable workflows (DBOS) over one transactional store (PostgreSQL), and pushes untrusted work out to isolated stations.

| Container | Role |
| --- | --- |
| `grindstone` | The control plane: kernel, factories, workflows, REST API and static UI, kernel MCP server and delivery adapters. It holds all authority and credentials. |
| `agent-host` | The agent station: a thin AHP host running agents over ACP (Claude Code for now; others by configuration). It holds model credentials only. |
| `runner` | The check station: it runs mechanical checks on a materialized subject, one job at a time, with no credentials. |
| `postgres` | The only store of records. |

Agents reach Grindstone only through a per-task MCP surface. They never deliver, and they never change the configuration that governs them. Higher station tiers (microVMs in R3, full VMs and attached hardware in R4) speak the same protocols, so the kernel does not change when they arrive.

## Roadmap

| Milestone | Outcome |
| --- | --- |
| M0 Foundations (closed) | Repository, CI and four services; spikes settled; M1 specified |
| M1 Walking skeleton | A hand-written ticket becomes a verified pull request through a skeleton SDLC factory, and Grindstone starts building itself |
| M2 Traceable intent | Full item model and relation graph; freshness computed; the `notes` factory proves the kernel neutral |
| M3 Safe change and cooperation | Findings flow back through reviewed ChangeSets; agents consult and delegate; parallel work across agent accounts, the delivery queue, and people as makers |
| M4 Discovery and planning | From an idea to approved tickets, decided in the browser |
| M5 MVP | Project memory, the outer loop, autonomy L2, day-to-day operations |

| Release | Outcome |
| --- | --- |
| R1 | Factories as separate packages; static reverse engineering that delegates code to SDLC |
| R2 | Snapshot and restore, semantic search, autonomy L3 and auto-merge, policy delivery of routine pull requests, further agents; the orchestrator in Assist and Checkpointed modes |
| R3 | microVM stations for untrusted code and dynamic analysis |
| R4 | Full-VM stations, hardware and computer use; a first hardware-adjacent factory |
| R5 | Autonomous builds: from a one-shot product idea to verified software, with acceptance tests written before the implementation and a fidelity audit against the idea |

Each release must close without a breaking change to the kernel SDK. If one needs a new kernel verb, kind or decision class, the kernel boundary was drawn wrong.

**Out of scope for the MVP:** more than one operator, any git host other than GitHub, Kubernetes or message brokers, separate vector or graph databases, a factory marketplace, agents talking to each other directly, and any merge that bypasses Grindstone's verification. The orchestrator comes after the MVP; the MVP lays its ground.

## Quality bars

Grindstone holds its own code, and everything it produces in any factory, to these bars:

- **Correctness**
- **Traceability**
- **Freshness**: computed, never stored.
- **Durability**: idempotent, resumable workflows.
- **Type safety**: Pydantic is the single source of types.
- **Reversibility**
- **Independence**: nothing proves its own work.
- **Simplicity**: the fewest moving parts. In factories, data beats code.

## Development

You need [uv](https://docs.astral.sh/uv/) 0.13.1, Node.js 24.22.0 with Corepack enabled (`corepack enable`), Docker with Compose, and GNU Make. uv and Corepack install Python 3.14.8 and pnpm from the pinned versions.

```sh
make setup      # install the locked Python and Node toolchains
make check      # lint, type checks, tests, fitness functions: what CI runs
make gen        # regenerate JSON Schemas and TypeScript after changing the Pydantic contracts
make up         # build and start the four services (creates dev secrets in secrets/)
make smoke      # start the stack, verify health, mounts and network isolation, stop
make fixture    # run the fixture project's tagged tests in the runner image
make benchmark  # generate the 20,000-item benchmark project
make help       # every target
```

| Path | Holds |
| --- | --- |
| `packages/grindstone/` | The control plane: twelve kernel modules and `grindstone.sdk`, the only API factories may import |
| `factories/sdlc/`, `factories/notes/` | The software-development factory and the code-free fixture factory |
| `runner/` | The check-station job executor (standard library only) |
| `agent-host/` | The agent station's host (TypeScript) |
| `packages/contracts-ts/` | TypeScript types generated from the Pydantic contracts |
| `docker/`, `compose.yaml` | Images and the one-host deployment |
| `scripts/ff/` | Architecture fitness functions |
| `docs/foundation/` | The foundation: the source of every commitment |
| `docs/specs/`, `docs/spikes/` | Specifications with their reviews, and spike reports |
| `docs/m0/` | Status, kickoff decisions, resolved versions, operator setup |

CI enforces the architecture through fitness functions. The kernel never imports a factory, and factories import only `grindstone.sdk`. Generated contracts must match their source. Every dependency is pinned exactly and every image by digest (`docs/m0/versions.md`). Every cited identifier must exist in the foundation.

## Contributing

Write the specification before the code. [`docs/foundation/grindstone-foundation.md`](docs/foundation/grindstone-foundation.md) holds every commitment. Specifications follow its planning playbook, and a session that did not write a specification reviews it. A choice that crosses a module or factory boundary is proposed as a decision record, not decided inline. Commits follow [Conventional Commits](https://www.conventionalcommits.org/), and pull requests are squash-merged into a protected `main`.

## License

[Apache License 2.0](LICENSE).
